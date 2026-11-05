"""Stage the local Tree 2 audit package. This program uses no network."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from pathlib import Path, PurePosixPath
import argparse
import datetime
import gzip
import hashlib
import json
import os
import re
import stat
import tarfile
import time

from package_policy import CHECKM1_MODEL_FILES, classify, prune_directory


BUNDLE = Path(__file__).resolve().parent
PROJECT = BUNDLE.parents[1]
PART_BYTES = 90 * 1024**2
DISK_RESERVE = 40 * 1024**3
TOP_LEVEL = (
    "analysis", "checkpoints", "config", "docs", "evidence", "logs", "manifests",
    "metadata", "patches", "qc", "raw", "recovery", "scripts", "state", "tools", "work",
)
ROOT_FILES = (
    "AGENTS.md", "README.md", "STATUS.md", "REBOOT_CHECKPOINT.md", "STARTUP_REPORT.md",
    ".gitignore", ".gitattributes",
)
GENERIC_RESULTS = {"results", "evidence"}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_row(stream, row):
    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reference(path):
    return {"path": path.relative_to(BUNDLE).as_posix(), "sha256": file_digest(path), "bytes": path.stat().st_size}


def reparse(status):
    return stat.S_ISLNK(status.st_mode) or bool(getattr(status, "st_file_attributes", 0) & 0x400)


def walk(directory, relative, omissions):
    reason = prune_directory(relative)
    if reason:
        write_row(omissions, {"path": relative.as_posix(), "type": "directory", "reason": reason})
        return
    with os.scandir(directory) as stream:
        for entry in stream:
            item = relative / entry.name
            info = entry.stat(follow_symlinks=False)
            if reparse(info):
                write_row(omissions, {"path": item.as_posix(), "type": "link_or_reparse", "reason": "link_not_dereferenced"})
            elif stat.S_ISDIR(info.st_mode):
                yield from walk(entry.path, item, omissions)
            elif stat.S_ISREG(info.st_mode):
                yield item, Path(entry.path), info
            else:
                write_row(omissions, {"path": item.as_posix(), "type": "special", "reason": "not_a_regular_file"})


def inventory():
    plans = BUNDLE / "inventory"
    plans.mkdir(exist_ok=True)
    if (plans / "COMMITTED.json").exists():
        return json.loads((plans / "COMMITTED.json").read_text(encoding="utf-8"))
    spool = plans / ("scan-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f"))
    spool.mkdir()
    counts, sizes, omitted = Counter(), Counter(), Counter()
    with ExitStack() as stack:
        skipped = stack.enter_context((spool / "omissions.ndjson").open("x", encoding="utf-8", newline="\n"))
        handles = {}

        def select(relative, path, info):
            group, reason = classify(relative, path)
            if group is None:
                omitted[reason] += 1
                write_row(skipped, {"path": relative.as_posix(), "type": "file", "bytes": info.st_size, "reason": reason})
                return
            # Separate large science stages so completed archives can survive interruption.
            if group in GENERIC_RESULTS and relative.parts[0] in ("analysis", "recovery") and len(relative.parts) > 2:
                group += "--" + re.sub(r"[^a-zA-Z0-9_-]", "_", relative.parts[1])
            if group not in handles:
                handles[group] = stack.enter_context((spool / (group + ".ndjson")).open("x", encoding="utf-8", newline="\n"))
            write_row(handles[group], {"path": relative.as_posix(), "bytes": info.st_size, "mtime_ns": info.st_mtime_ns})
            counts[group] += 1
            sizes[group] += info.st_size

        for name in ROOT_FILES:
            path = PROJECT / name
            if path.is_file():
                select(PurePosixPath(name), path, path.stat())
        for name in TOP_LEVEL:
            root = PROJECT / name
            if not root.is_dir():
                continue
            for relative, path, info in walk(root, PurePosixPath(name), skipped):
                select(relative, path, info)
            print(f"Inventoried {name}: {sum(counts.values()):,} included, {sum(omitted.values()):,} file omissions", flush=True)
    result = {
        "source_snapshot_utc": utc(),
        "spool": spool.relative_to(BUNDLE).as_posix(),
        "groups": {group: {"members": counts[group], "unpacked_bytes": sizes[group]} for group in sorted(counts)},
        "file_omissions": dict(omitted),
    }
    atomic_json(plans / "COMMITTED.json", result)
    return result


def include_late_records(snapshot):
    """Reconcile audit records added to the scope while a prior scan was running."""
    late_group = "methods--late_records"
    if late_group in snapshot["groups"]:
        return
    spool = BUNDLE / snapshot["spool"]
    candidates = {name: "methods" for name in ROOT_FILES} | {name: "data_provenance" for name in CHECKM1_MODEL_FILES}
    existing = set()
    for group in ("methods", "data_provenance"):
        planned = spool / (group + ".ndjson")
        if planned.exists():
            with planned.open(encoding="utf-8") as stream:
                existing.update(row for line in stream if (row := json.loads(line)["path"]) in candidates)
    records = []
    for name, expected_group in sorted(candidates.items()):
        path = PROJECT / name
        if name in existing or not path.is_file():
            continue
        group, reason = classify(PurePosixPath(name), path)
        if group != expected_group:
            raise RuntimeError(f"Late audit record could not be included: {name}: {reason}")
        info = path.stat()
        records.append({"path": name, "bytes": info.st_size, "mtime_ns": info.st_mtime_ns})
    if not records:
        return
    with (spool / (late_group + ".ndjson")).open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            write_row(stream, record)
    selected = {record["path"] for record in records}
    omissions = spool / "omissions.ndjson"
    temporary = omissions.with_suffix(".ndjson.partial")
    with omissions.open(encoding="utf-8") as source, temporary.open("w", encoding="utf-8", newline="\n") as dest:
        for line in source:
            record = json.loads(line)
            if record["path"] in selected:
                snapshot["file_omissions"][record["reason"]] -= 1
            else:
                dest.write(line)
    os.replace(temporary, omissions)
    snapshot["groups"][late_group] = {"members": len(records), "unpacked_bytes": sum(record["bytes"] for record in records)}
    atomic_json(BUNDLE / "inventory" / "COMMITTED.json", snapshot)


def include_verified_proteins(snapshot):
    group = "results--verified_protein_supplement"
    if group in snapshot["groups"]:
        return
    receipt_paths = [BUNDLE / name for name in ("verified_protein_derivatives.json", "verified_provider_proteins.json")]
    if not all(path.is_file() for path in receipt_paths):
        return
    proofs = {}
    for receipt_path in receipt_paths:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt["status"] != "PASS":
            raise RuntimeError(f"Protein audit receipt did not pass: {receipt_path.name}")
        for record in receipt["proteins"]:
            proofs[record["path"]] = record
    spool = BUNDLE / snapshot["spool"]
    omitted = spool / "omissions.ndjson"
    temporary = omitted.with_suffix(".ndjson.partial")
    accepted = []
    with omitted.open(encoding="utf-8") as source, temporary.open("w", encoding="utf-8", newline="\n") as dest:
        for line in source:
            row = json.loads(line)
            rel = row["path"]
            if rel not in proofs or row["reason"] != "nucleotide_or_ambiguous_fasta_payload":
                dest.write(line)
                continue
            path = PROJECT / rel
            proof = proofs.pop(rel)
            info = path.lstat()
            if path.suffix.lower() not in (".faa", ".fasta") or reparse(info) or not stat.S_ISREG(info.st_mode) or (
                    info.st_size != proof["bytes"] or file_digest(path) != proof["sha256"]):
                raise RuntimeError(f"Independently proven protein file changed: {rel}")
            accepted.append({"path": rel, "bytes": info.st_size, "mtime_ns": info.st_mtime_ns})
            snapshot["file_omissions"][row["reason"]] -= 1
    if not accepted:
        return
    if proofs:
        raise RuntimeError(f"Protein supplement scope differs from original omissions: {sorted(proofs)}")
    with (spool / (group + ".ndjson")).open("w", encoding="utf-8", newline="\n") as stream:
        for row in accepted:
            write_row(stream, row)
    os.replace(temporary, omitted)
    snapshot["groups"][group] = {"members": len(accepted), "unpacked_bytes": sum(row["bytes"] for row in accepted)}
    atomic_json(BUNDLE / "inventory" / "COMMITTED.json", snapshot)


class PartWriter:
    def __init__(self, folder, group):
        self.folder = folder
        self.group = group
        self.parts = []
        self.stream = None
        self.size = 0
        self.digest = None

    def open_part(self):
        import shutil
        if shutil.disk_usage(BUNDLE).free < DISK_RESERVE + PART_BYTES:
            raise RuntimeError("Audit packaging reached the 40 GiB disk reserve")
        self.path = self.folder / f"{self.group}.tar.gz.part{len(self.parts) + 1:04d}"
        self.temporary = self.path.with_suffix(self.path.suffix + ".partial")
        self.stream = self.temporary.open("xb")
        self.digest = hashlib.sha256()
        self.size = 0

    def write(self, data):
        view = memoryview(data)
        length = len(view)
        while view:
            if self.stream is None:
                self.open_part()
            chunk = view[: PART_BYTES - self.size]
            self.stream.write(chunk)
            self.digest.update(chunk)
            self.size += len(chunk)
            view = view[len(chunk):]
            if self.size == PART_BYTES:
                self.finish_part()
        return length

    def flush(self):
        if self.stream:
            self.stream.flush()

    def finish_part(self):
        if self.stream is None:
            return
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        os.replace(self.temporary, self.path)
        self.parts.append({"path": self.path.relative_to(BUNDLE).as_posix(), "sha256": self.digest.hexdigest(), "bytes": self.size})
        self.stream = None


class DigestReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size):
        chunk = self.stream.read(size)
        self.digest.update(chunk)
        return chunk


def pack_group(group, expected, spool):
    group_dir = BUNDLE / "payload" / group
    group_dir.mkdir(parents=True, exist_ok=True)
    committed = group_dir / "COMMITTED.json"
    if committed.exists():
        result = json.loads(committed.read_text(encoding="utf-8"))
        assert {key: result[key] for key in expected} == expected
        assert reference(BUNDLE / result["manifest"]["path"]) == result["manifest"]
        for part in result["parts"]:
            assert (BUNDLE / part["path"]).stat().st_size == part["bytes"]
        return result
    attempt = group_dir / datetime.datetime.now(datetime.timezone.utc).strftime("attempt-%Y%m%dT%H%M%S%f")
    attempt.mkdir()
    writer = PartWriter(attempt, group)
    members, unpacked = 0, 0
    last_progress = 0.0
    manifest_path = attempt / "files.ndjson"
    try:
        with (spool / (group + ".ndjson")).open(encoding="utf-8") as paths, manifest_path.open("x", encoding="utf-8", newline="\n") as manifest:
            with gzip.GzipFile(fileobj=writer, filename="", mode="wb", compresslevel=1, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT,
                                  bufsize=256 * 1024, copybufsize=1024**2) as archive:
                    for line in paths:
                        item = json.loads(line)
                        relative = PurePosixPath(item["path"])
                        path = PROJECT.joinpath(*relative.parts)
                        before = path.lstat()
                        if reparse(before) or not stat.S_ISREG(before.st_mode) or (before.st_size, before.st_mtime_ns) != (item["bytes"], item["mtime_ns"]):
                            raise RuntimeError(f"Source changed after inventory: {relative}")
                        info = tarfile.TarInfo(relative.as_posix())
                        info.size = before.st_size
                        info.mtime = int(before.st_mtime)
                        info.mode = 0o755 if path.suffix.lower() in (".sh", ".py") else 0o644
                        with path.open("rb") as stream:
                            source = DigestReader(stream)
                            archive.addfile(info, source)
                            after = os.fstat(stream.fileno())
                        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
                            raise RuntimeError(f"Source changed while being read: {relative}")
                        write_row(manifest, {"path": relative.as_posix(), "sha256": source.digest.hexdigest(), "bytes": info.size, "group": group})
                        members += 1
                        unpacked += info.size
                        if time.monotonic() - last_progress > 30:
                            atomic_json(group_dir / "progress.json", {
                                "state": "PACKING", "group": group, "members": members,
                                "total_members": expected["members"], "unpacked_bytes": unpacked, "at_utc": utc(),
                            })
                            last_progress = time.monotonic()
        writer.finish_part()
    finally:
        if writer.stream and not writer.stream.closed:
            writer.stream.close()
    assert members == expected["members"] and unpacked == expected["unpacked_bytes"]
    result = {"group": group, "parts": writer.parts, "members": members, "unpacked_bytes": unpacked,
              "manifest": reference(manifest_path), "completed_utc": utc()}
    atomic_json(committed, result)
    return result


def pack_task(item):
    group, expected, spool = item
    result = pack_group(group, expected, spool)
    print(f"Packed {group}: {result['members']:,} files, {len(result['parts'])} parts", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=1)
    args = parser.parse_args()
    if (BUNDLE / "package_index.json").exists():
        raise RuntimeError("This bundle is already assembled")
    snapshot = inventory()
    include_late_records(snapshot)
    include_verified_proteins(snapshot)
    if args.inventory_only:
        print(json.dumps(snapshot, indent=2))
        return
    spool = BUNDLE / snapshot["spool"]
    atomic_json(BUNDLE / "build_progress.json", {"state": "PACKING", "at_utc": utc()})

    # Balance byte-heavy groups and small-file-heavy groups across independent processes.
    groups = sorted(snapshot["groups"].items(), key=lambda item: item[1]["unpacked_bytes"] + item[1]["members"] * 16384,
                    reverse=True)
    tasks = ((group, expected, spool) for group, expected in groups)
    if args.workers == 1:
        results = [pack_task(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as workers:
            results = list(workers.map(pack_task, tasks))
    results.sort(key=lambda result: result["group"])
    manifest = BUNDLE / "files.ndjson"
    temporary = manifest.with_suffix(".ndjson.partial")
    import shutil
    with temporary.open("wb") as combined:
        for result in results:
            with (BUNDLE / result["manifest"]["path"]).open("rb") as source:
                shutil.copyfileobj(source, combined, 1024**2)
        combined.flush()
        os.fsync(combined.fileno())
    os.replace(temporary, manifest)
    index = {
        "schema": "TREE2_AUDIT_BUNDLE_V001", "status": "COMPLETE",
        "source_snapshot_utc": snapshot["source_snapshot_utc"], "created_utc": utc(),
        "file_manifest": reference(manifest), "omissions": reference(spool / "omissions.ndjson"),
        "archives": results, "members": sum(result["members"] for result in results),
        "unpacked_bytes": sum(result["unpacked_bytes"] for result in results),
        "payload_bytes": sum(part["bytes"] for result in results for part in result["parts"]),
    }
    atomic_json(BUNDLE / "package_index.json", index)
    atomic_json(BUNDLE / "build_progress.json", {"state": "PACKED_AWAITING_INDEPENDENT_VERIFICATION", "at_utc": utc()})
    print(json.dumps({key: index[key] for key in ("status", "members", "unpacked_bytes", "payload_bytes")}))


if __name__ == "__main__":
    main()
