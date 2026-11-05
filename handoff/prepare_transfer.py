"""Derive and verify the release bundle without the signed registry URLs."""
import gzip
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit, urlunsplit


PUBLISH = Path(__file__).resolve().parent
SOURCE = PUBLISH.parent
TRANSFER = PUBLISH / "transfer_bundle"
RESTRICTED = "evidence/model_routes/oci_metadata_20261027/registry_manifest_receipts.json"
sys.path.insert(0, str(SOURCE))
import build_bundle as builder
from verify_and_restore import SplitStream


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def atomic_stream(path, write):
    temporary = path.with_suffix(path.suffix + ".partial")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("wb") as stream:
        write(stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def clean_evidence():
    original = load(SOURCE / "payload/evidence/COMMITTED.json")
    group = TRANSFER / "payload/evidence"
    group.mkdir(parents=True, exist_ok=True)
    committed = group / "COMMITTED.json"
    if committed.exists():
        return load(committed)
    attempt = group / "publication-filtered-v001"
    attempt.mkdir(exist_ok=False)
    builder.BUNDLE = TRANSFER
    writer = builder.PartWriter(attempt, "evidence")
    filtered_manifest = attempt / "files.ndjson"
    omit = None
    total = members = 0
    with SplitStream(SOURCE, original["parts"]) as parts, io.BufferedReader(parts) as compressed_input:
        with gzip.GzipFile(fileobj=compressed_input, mode="rb") as decompressed:
            with tarfile.open(fileobj=decompressed, mode="r|", bufsize=256 * 1024) as raw_archive:
                with gzip.GzipFile(fileobj=writer, mode="wb", filename="", mtime=0, compresslevel=1) as compressed:
                    with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT,
                                      bufsize=256 * 1024) as archive, filtered_manifest.open("x", encoding="utf-8", newline="\n") as manifest:
                        with (SOURCE / original["manifest"]["path"]).open(encoding="utf-8") as refs:
                            for entry, line in zip(iter(raw_archive.next, None), refs, strict=True):
                                raw_archive.members.clear()
                                row = json.loads(line)
                                require(entry.isfile() and entry.name == row["path"] and entry.size == row["bytes"], "Evidence tar does not match source manifest")
                                with raw_archive.extractfile(entry) as stream:
                                    if entry.name == RESTRICTED:
                                        require(omit is None and entry.size < 256 * 1024, "Unexpected registry receipt")
                                        value = json.load(stream)
                                        redactions = 0
                                        for record in value["records"]:
                                            location = record.get("location")
                                            if isinstance(location, str) and "X-Amz-Credential=" in location:
                                                parsed = urlsplit(location)
                                                record["location"] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
                                                record["location_query_omitted"] = True
                                                redactions += 1
                                        require(redactions == 2, "Registry receipt signed-query count changed")
                                        omit = {"path": RESTRICTED, "sha256": row["sha256"], "bytes": row["bytes"],
                                                "type": "file", "reason": "original_registry_receipt_contains_presigned_URL_credentials"}
                                        builder.atomic_json(PUBLISH / "registry-receipt-sanitized.json", {
                                            "original": omit, "redacted_query_strings": redactions, "receipt": value,
                                        })
                                        builder.atomic_json(PUBLISH / "release_exclusion.json", omit)
                                        continue
                                    source = builder.DigestReader(stream)
                                    clean = tarfile.TarInfo(entry.name)
                                    clean.size, clean.mtime, clean.mode = entry.size, entry.mtime, entry.mode
                                    archive.addfile(clean, source)
                                    require(source.digest.hexdigest() == row["sha256"], f"Evidence hash changed: {entry.name}")
                                manifest.write(line)
                                members += 1
                                total += entry.size
                        manifest.flush()
                        os.fsync(manifest.fileno())
            while decompressed.read(1024**2):
                pass
        require(not compressed_input.read(1) and parts.complete, "Original evidence parts were not fully checked")
    writer.finish_part()
    require(omit is not None and members + 1 == original["members"] and total + omit["bytes"] == original["unpacked_bytes"],
            "Evidence members and byte counts changed unexpectedly")
    result = {"group": "evidence", "parts": writer.parts, "members": members, "unpacked_bytes": total,
              "manifest": builder.reference(filtered_manifest), "completed_utc": builder.utc()}
    builder.atomic_json(committed, result)
    return result


def link_source(relative):
    original = SOURCE / relative
    path = TRANSFER / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        os.link(original, path)
    require(path.samefile(original), f"Unexpected staged path: {relative}")


def assemble():
    builder.BUNDLE = TRANSFER
    replacement = clean_evidence()
    index = load(SOURCE / "package_index.json")
    exclusion = load(PUBLISH / "release_exclusion.json")
    groups = []
    for group in index["archives"]:
        if group["group"] == "evidence":
            groups.append(replacement)
            continue
        groups.append(group)
        for item in (group["manifest"], *group["parts"]):
            link_source(item["path"])

    def copy_omissions(stream):
        with (SOURCE / index["omissions"]["path"]).open("rb") as original:
            shutil.copyfileobj(original, stream)
        stream.write((json.dumps(exclusion, separators=(",", ":")) + "\n").encode())

    omissions = TRANSFER / index["omissions"]["path"]
    atomic_stream(omissions, copy_omissions)
    combined = TRANSFER / "files.ndjson"

    def copy_manifests(stream):
        for group in groups:
            with (TRANSFER / group["manifest"]["path"]).open("rb") as source:
                shutil.copyfileobj(source, stream)

    atomic_stream(combined, copy_manifests)
    index.update(archives=groups, omissions=builder.reference(omissions), file_manifest=builder.reference(combined),
                 members=sum(group["members"] for group in groups), unpacked_bytes=sum(group["unpacked_bytes"] for group in groups),
                 payload_bytes=sum(part["bytes"] for group in groups for part in group["parts"]),
                 created_utc=builder.utc(), release_scope="one signed registry receipt replaced by separately documented sanitized copy")
    builder.atomic_json(TRANSFER / "package_index.json", index)

    print("Verifying the exact release-scoped snapshot", flush=True)
    process = subprocess.run([sys.executable, "-B", "-u", str(SOURCE / "verify_and_restore.py"), str(TRANSFER)], check=False)
    builder.atomic_json(TRANSFER / "VERIFICATION.json", {
        "status": "PASS" if process.returncode == 0 else "FAIL", "exit_code": process.returncode,
        "index": builder.reference(TRANSFER / "package_index.json"), "release_exclusion": exclusion,
        "members": index["members"], "unpacked_bytes": index["unpacked_bytes"], "payload_bytes": index["payload_bytes"],
        "verified_utc": builder.utc(),
    })
    return process.returncode


if __name__ == "__main__":
    if sys.argv[1:] == ["--filter-evidence"]:
        print(json.dumps(clean_evidence()), flush=True)
    elif not sys.argv[1:]:
        raise SystemExit(assemble())
    else:
        raise SystemExit("usage: prepare_transfer.py [--filter-evidence]")
