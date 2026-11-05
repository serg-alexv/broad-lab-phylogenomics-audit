#!/usr/bin/env python3
"""Verify every byte and member of a split Tree 2 handoff bundle.

Usage: python verify_and_restore.py [BUNDLE] [--restore NEW_DIRECTORY]
The default bundle is the directory containing this script.
Verification uses a temporary disk index inside the writable bundle directory.
Ordered group manifests can stand in for an omitted combined files.ndjson.
Restoring case-distinct evidence requires a case-sensitive destination, such as
a native Linux filesystem or a WSL distribution's Linux filesystem.
"""

import argparse
from contextlib import closing
from functools import lru_cache
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tarfile
import tempfile
import unicodedata


BLOCK = 1024 * 1024
TAR_BUFFER = 64 * 1024
MAX_INDEX = 8 * BLOCK
MAX_MANIFEST_LINE = 64 * 1024
MARKER = ".tree2-restore-incomplete"
DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³])", re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(data):
    return json.loads(data, object_pairs_hook=unique_object)


def portable_path(value):
    require(isinstance(value, str) and value, f"Invalid relative path: {value!r}")
    require(len(value.encode("utf-8")) <= 4096, "Relative path exceeds the portable length limit")
    parts = value.split("/")
    for part in parts:
        require(len(part.encode("utf-8")) <= 255 and part not in ("", ".", "..")
                and not part.endswith((" ", "."))
                and not DEVICE.fullmatch(part.split(".", 1)[0].rstrip(" "))
                and not any(ord(c) < 32 or c in '<>:"\\|?*' for c in part),
                f"Unsafe or nonportable relative path: {value!r}")
    return parts


def portable_key(name):
    return unicodedata.normalize("NFC", name).casefold()


def disk_key(name):
    return hashlib.sha256(name.encode("utf-8")).digest()


def bundle_file(root, name):
    path = root.joinpath(*portable_path(name))
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(),
                f"Bundle path contains a link: {name}")
    require(path.resolve(strict=True).is_relative_to(root), f"Bundle path escapes root: {name}")
    require(stat.S_ISREG(path.stat().st_mode), f"Bundle path is not a regular file: {name}")
    return path


def natural_number(value, label):
    require(type(value) is int and value >= 0, f"Invalid {label}")
    return value


def check_reference(ref):
    portable_path(ref["path"])
    natural_number(ref["bytes"], "byte count")
    require(isinstance(ref["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]),
            f"Invalid SHA256 for {ref['path']}")


def check_digest(ref, count, digest):
    require(count == ref["bytes"] and digest.hexdigest() == ref["sha256"],
            f"Size or SHA256 mismatch: {ref['path']}")


class SplitStream(io.RawIOBase):
    """Concatenate read-only pieces while checking each piece independently."""

    def __init__(self, root, parts):
        super().__init__()
        self.root = root
        self.parts = iter(parts)
        self.ref = None
        self.stream = None
        self.complete = False

    def readable(self):
        return True

    def readinto(self, buffer):
        if not buffer:
            return 0
        while not self.complete:
            if self.stream is None:
                self.ref = next(self.parts, None)
                if self.ref is None:
                    self.complete = True
                    break
                self.stream = bundle_file(self.root, self.ref["path"]).open("rb")
                self.count = 0
                self.digest = hashlib.sha256()
            count = self.stream.readinto(buffer)
            if count:
                self.count += count
                require(self.count <= self.ref["bytes"], f"Unexpected extra bytes: {self.ref['path']}")
                self.digest.update(memoryview(buffer)[:count])
                return count
            check_digest(self.ref, self.count, self.digest)
            self.stream.close()
            self.stream = None
        return 0

    def close(self):
        try:
            if self.stream is not None:
                self.stream.close()
        finally:
            super().close()


class TarInput:
    """Observe the end header without handing extraction to tarfile."""

    def __init__(self, stream):
        self.stream = stream
        self.last = b""
        self.offset = 0

    def read(self, count):
        data = self.stream.read(count)
        if data:
            self.last = data
            self.offset += len(data)
        return data


def check_physical_manifest(root, ref):
    path = root.joinpath(*portable_path(ref["path"]))
    try:
        path.lstat()
    except FileNotFoundError:
        return
    digest = hashlib.sha256()
    count = 0
    with bundle_file(root, ref["path"]).open("rb") as stream:
        for data in iter(lambda: stream.read(BLOCK), b""):
            digest.update(data)
            count += len(data)
    check_digest(ref, count, digest)


def manifest_lines(root, combined, archives, grouped):
    if grouped:
        # Reconstruct the builder's literal concatenation in archive order.
        # A supplied combined file must pass independently as well.
        check_physical_manifest(root, combined)
        sources = [(archive["group"], archive["manifest"]) for archive in archives]
        combined_digest = hashlib.sha256()
        combined_count = 0
    else:
        sources = [(None, combined)]

    for group, ref in sources:
        digest = hashlib.sha256()
        count = 0
        with bundle_file(root, ref["path"]).open("rb") as stream:
            for line in iter(lambda: stream.readline(MAX_MANIFEST_LINE + 1), b""):
                require(len(line) <= MAX_MANIFEST_LINE, "Manifest line exceeds its size limit")
                digest.update(line)
                count += len(line)
                if grouped:
                    require(line.endswith(b"\n"), f"Group manifest has an unterminated record: {group}")
                    combined_digest.update(line)
                    combined_count += len(line)
                yield group, line
        check_digest(ref, count, digest)
    if grouped:
        check_digest(combined, combined_count, combined_digest)


def load_inventory(root, database):
    with bundle_file(root, "package_index.json").open("rb") as stream:
        index_bytes = stream.read(MAX_INDEX + 1)
    require(len(index_bytes) <= MAX_INDEX, "Bundle index exceeds its size limit")
    index = load_json(index_bytes)
    require(index["schema"] == "TREE2_AUDIT_BUNDLE_V001" and index["status"] == "COMPLETE",
            "Expected a complete Tree 2 audit bundle")
    manifest = index["file_manifest"]
    check_reference(manifest)
    groups = {}
    archives = index["archives"]
    group_manifest_presence = ["manifest" in archive for archive in archives]
    grouped = any(group_manifest_presence)
    require(not grouped or all(group_manifest_presence), "Index supplies an incomplete set of group manifests")
    bundle_names = {portable_key("package_index.json"), portable_key(manifest["path"])}
    require(len(bundle_names) == 2, "Index and manifest paths collide")
    for archive in archives:
        group = archive["group"]
        require(isinstance(group, str) and group and group not in groups, "Invalid or duplicate archive group")
        natural_number(archive["members"], "group member count")
        natural_number(archive["unpacked_bytes"], "group unpacked byte count")
        if grouped:
            ref = archive["manifest"]
            check_reference(ref)
            key = portable_key(ref["path"])
            require(key not in bundle_names, f"Duplicate or colliding group manifest: {ref['path']}")
            bundle_names.add(key)
        require(isinstance(archive["parts"], list) and archive["parts"], f"Group has no parts: {group}")
        for ref in archive["parts"]:
            check_reference(ref)
            key = portable_key(ref["path"])
            require(ref["bytes"] > 0 and key not in bundle_names, f"Empty, duplicate or colliding part: {ref['path']}")
            bundle_names.add(key)
        groups[group] = [0, 0]
    require(groups, "No archive groups in the index")

    # This index is disposable. Limit the SQLite page cache and avoid a large
    # transaction journal. The original bundle is opened read-only throughout.
    database.execute("PRAGMA cache_size = -32768")
    database.execute("PRAGMA temp_store = FILE")
    database.execute("PRAGMA journal_mode = OFF")
    database.execute("PRAGMA synchronous = OFF")
    database.execute("""
        CREATE TABLE nodes (
            key BLOB PRIMARY KEY,
            name TEXT NOT NULL,
            group_name TEXT,
            size INTEGER,
            sha256 BLOB,
            checked INTEGER NOT NULL DEFAULT 0
        ) WITHOUT ROWID
    """)
    database.execute("INSERT INTO nodes (key, name, group_name) VALUES (?, ?, '')",
                     (disk_key(MARKER), MARKER))

    @lru_cache(maxsize=4096)
    def register_directory(name):
        key = disk_key(name)
        created = database.execute("INSERT OR IGNORE INTO nodes (key, name) VALUES (?, ?)", (key, name))
        if created.rowcount == 0:
            existing = database.execute("SELECT name, group_name FROM nodes WHERE key = ?", (key,)).fetchone()
            require(existing == (name, None), f"File and directory path conflict: {name}")

    entries = 0
    for manifest_group, line in manifest_lines(root, manifest, archives, grouped):
        ref = load_json(line)
        check_reference(ref)
        name = ref["path"]
        parts = portable_path(name)
        group = ref["group"]
        require(group in groups, f"Unknown manifest group: {group!r}")
        require(manifest_group is None or group == manifest_group, f"Record is in the wrong group manifest: {name}")
        for length in range(1, len(parts)):
            register_directory("/".join(parts[:length]))
        try:
            database.execute("INSERT INTO nodes (key, name, group_name, size, sha256) VALUES (?, ?, ?, ?, ?)",
                             (disk_key(name), name, group, ref["bytes"], bytes.fromhex(ref["sha256"])))
        except sqlite3.IntegrityError:
            raise ValueError(f"File and directory path conflict or duplicate manifest file: {name}") from None
        groups[group][0] += 1
        groups[group][1] += ref["bytes"]
        entries += 1
        if entries % 250000 == 0:
            database.commit()
            print(f"Indexed {entries:,} manifest files", flush=True)
    for archive in archives:
        require(groups[archive["group"]] == [archive["members"], archive["unpacked_bytes"]],
                f"Index and manifest group totals differ: {archive['group']}")
    database.commit()
    return archives


def filesystem_aliases(path):
    """Probe actual filesystem name equivalence in an otherwise empty directory."""
    uppercase = path / "CaseProbe"
    composed = path / "\u00e9"
    created = []
    try:
        uppercase.touch(exist_ok=False)
        created.append(uppercase)
        composed.touch(exist_ok=False)
        created.append(composed)
        return (path / "caseprobe").exists(), (path / "e\u0301").exists()
    finally:
        for item in created:
            item.unlink(missing_ok=True)


def preflight_restore(destination, database):
    # Probe the destination itself and a newly created child, because some
    # filesystems can apply case sensitivity per directory.
    root_aliases = filesystem_aliases(destination)
    with tempfile.TemporaryDirectory(prefix=".tree2-name-test-", dir=destination) as probe:
        child_aliases = filesystem_aliases(Path(probe))
    case_alias = root_aliases[0] or child_aliases[0]
    unicode_alias = root_aliases[1] or child_aliases[1]
    if not case_alias and not unicode_alias:
        return

    database.execute("CREATE TABLE restore_names (key BLOB PRIMARY KEY, name TEXT) WITHOUT ROWID")
    for (name,) in database.execute("SELECT name FROM nodes"):
        normalized = unicodedata.normalize("NFC", name) if unicode_alias else name
        normalized = normalized.casefold() if case_alias else normalized
        key = disk_key(normalized)
        try:
            database.execute("INSERT INTO restore_names VALUES (?, ?)", (key, name))
        except sqlite3.IntegrityError:
            other = database.execute("SELECT name FROM restore_names WHERE key = ?", (key,)).fetchone()[0]
            raise ValueError(f"Destination filesystem aliases {other!r} and {name!r}. "
                             "Choose a new destination on a filesystem that preserves both names "
                             "(for example, a native Linux or WSL Linux filesystem).") from None
    database.execute("DROP TABLE restore_names")
    database.commit()


def verify_member(archive, member, ref, destination):
    digest = hashlib.sha256()
    count = 0
    path = None
    output = None
    if destination is not None:
        path = destination.joinpath(*portable_path(ref["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        output = path.open("xb")
    try:
        with archive.extractfile(member) as stream:
            for data in iter(lambda: stream.read(BLOCK), b""):
                digest.update(data)
                count += len(data)
                if output is not None:
                    output.write(data)
        check_digest(ref, count, digest)
        if output is not None:
            output.close()
    except BaseException:
        if output is not None:
            output.close()
            path.unlink()
        raise


def verify_archive(root, archive_ref, database, destination):
    seen = 0
    end_of_members = 0
    group = archive_ref["group"]
    with SplitStream(root, archive_ref["parts"]) as parts, io.BufferedReader(parts) as compressed:
        with gzip.GzipFile(fileobj=compressed, mode="rb") as uncompressed:
            source = TarInput(uncompressed)
            with tarfile.open(fileobj=source, mode="r|", bufsize=TAR_BUFFER) as archive:
                for member in iter(archive.next, None):
                    # Python versions before 3.13 cache TarInfo even in streaming
                    # mode. Only ordinary files are allowed, so we need no cache.
                    archive.members.clear()
                    name = member.name
                    require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and member.sparse is None
                            and not member.linkname, f"Tar member is not an ordinary regular file: {name!r}")
                    key = disk_key(name)
                    indexed = database.execute("SELECT name, group_name, size, sha256, checked FROM nodes WHERE key = ?",
                                               (key,)).fetchone()
                    require(indexed is not None and indexed[:2] == (name, group) and not indexed[4],
                            f"Unexpected or duplicate tar member: {name!r}")
                    require(member.size == indexed[2], f"Tar member size differs: {name}")
                    ref = {"path": name, "bytes": indexed[2], "sha256": indexed[3].hex()}
                    verify_member(archive, member, ref, destination)
                    database.execute("UPDATE nodes SET checked = 1 WHERE key = ?", (key,))
                    seen += 1
                    if seen % 250000 == 0:
                        database.commit()
                        print(f"Verified {seen:,} files so far in {group}", flush=True)
                    end_of_members = member.offset_data + (
                        (member.size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE * tarfile.BLOCKSIZE
                    )
            end_position = end_of_members - (source.offset - len(source.last))
            require(0 <= end_position <= len(source.last) - tarfile.BLOCKSIZE,
                    "Tar first end block is missing")
            trailer = source.last[end_position:]
            require(not any(trailer), "Nonzero data after the last tar member")
            trailer_size = len(trailer)
            for data in iter(lambda: uncompressed.read(BLOCK), b""):
                require(not any(data), "Nonzero data after the tar end marker")
                trailer_size += len(data)
            require(trailer_size >= 2 * tarfile.BLOCKSIZE and trailer_size % tarfile.BLOCKSIZE == 0,
                    "Missing tar end blocks or malformed padding")
        require(not compressed.read(1) and parts.complete, "Compressed payload was not fully verified")
    require(seen == archive_ref["members"], f"Missing tar members in group: {group}")
    database.commit()


def run(bundle, restore):
    root = bundle.resolve(strict=True)
    require(root.is_dir(), "Bundle root must be a directory")
    destination = None
    if restore is not None:
        require(restore.name not in ("", ".", ".."), "Specify a new destination directory")
        destination = restore.parent.resolve(strict=True) / restore.name
        require(not destination.is_relative_to(root), "Restore destination must be outside the bundle")
    with tempfile.TemporaryDirectory(prefix=".tree2-verify-", dir=root) as scratch:
        with closing(sqlite3.connect(Path(scratch) / "inventory.sqlite")) as database:
            archives = load_inventory(root, database)
            if destination is not None:
                destination.mkdir(exist_ok=False)
                with (destination / MARKER).open("x", encoding="utf-8") as marker:
                    marker.write("Restore has not passed complete bundle verification.\n")
                preflight_restore(destination, database)
            for archive in archives:
                verify_archive(root, archive, database, destination)
                print(f"Verified {archive['group']}: {archive['members']:,} files, "
                      f"{archive['unpacked_bytes']:,} bytes", flush=True)
    if destination is not None:
        (destination / MARKER).unlink()
        print(f"Restored and verified: {destination}")
    else:
        print("Bundle verification passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--restore", type=Path, metavar="NEW_DIRECTORY",
                        help="Restore files into a destination that does not yet exist")
    args = parser.parse_args()
    try:
        run(args.bundle, args.restore)
    except (OSError, ValueError, KeyError, TypeError, EOFError, OverflowError, sqlite3.Error, tarfile.TarError) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
