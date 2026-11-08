#!/usr/bin/env python3
"""Read-only, frozen C009 release-archive raw HMMER QA. NEVER promotes a cohort."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sys
import tarfile

ARCHIVE_SHA = "ff49a11de531ecce280df61d8213dd15eca62d66af17392bb0b6a3c97c14a2dd"
ARCHIVE_SIZE = 93641823
MEMBERS = 169722
DF_MULTISET_SHA = "67bb7fbd1b685dd1d23fc378420fafc8915d94d75694f6f842b1c854bd1747d0"
ENGINES = {"PADLOC": "PADLOC2_DB2", "DefenseFinder": "DefenseFinder3_models3.1_Cas3.1"}
PATTERN = re.compile(r"(?:^|/)rows/(GC[AF]_\d{9}\.\d+)/(PADLOC|DefenseFinder)/(.+)$")

def require(ok, detail):
    if not ok:
        raise ValueError(detail)

def digest(f):
    h = hashlib.sha256()
    length = 0
    tail = b""
    for data in iter(lambda: f.read(1048576), b""):
        h.update(data)
        length += len(data)
        tail = (tail + data)[-4096:]
    return h.hexdigest(), length, tail

def key(path):
    m = PATTERN.search(str(path).replace("\\", "/"))
    return m.groups() if m else None

def refkey(ref):
    require(isinstance(ref, dict) and isinstance(ref.get("path"), str), "Bad reference")
    k = key(ref["path"])
    require(k is not None and isinstance(ref.get("bytes"), int)
            and re.fullmatch(r"[0-9a-f]{64}", ref.get("sha256", "")) is not None,
            "Bad ref SHA/path/size: " + str(ref.get("path")))
    return k

def getjson(tar, member):
    require(member.isfile() and member.size < 33554432, "Unexpected JSON member")
    f = tar.extractfile(member)
    require(f is not None, "Cannot open " + member.name)
    raw = f.read()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest(), len(raw)

def scan_metadata(archive):
    phases, receipts, complete = {}, {}, []
    n = 0
    with tarfile.open(archive, "r|gz") as tar:
        for m in tar:
            n += 1
            k = key(m.name)
            if k is None:
                if m.name.endswith("/COHORT_COMPLETE.json"):
                    complete.append(getjson(tar, m)[0])
                continue
            acc, engine, tail = k
            if tail == "COMMITTED.json":
                require((acc, engine) not in phases, "Duplicate phase: " + str(k))
                phases[acc, engine] = getjson(tar, m)
            elif tail.startswith("HMMER_receipts/") and tail.endswith(".json"):
                require(k not in receipts, "Duplicate receipt: " + str(k))
                receipts[k] = getjson(tar, m)
    require(n == MEMBERS, "Wrong archive member count: " + str(n))
    require(len(complete) == 1, "Need one source COHORT_COMPLETE.json")
    c = complete[0]
    targets = set(c["selected_accessions"])
    require(len(targets) == 20 and len(c["selected_accessions"]) == 20,
            "Wrong C009 selected-accession cardinality")
    require(set(phases) == {(a, e) for a in targets for e in ENGINES},
            "40 phases are not exactly bound to the 20 selected accessions")
    cr = c["engine_phase_commits"]
    require(len(cr) == 40, "Wrong C009 source phase references")
    source_refs = {(refkey(r), r["sha256"], r["bytes"]) for r in cr}
    require(len(source_refs) == 40, "Duplicate source phase references")
    for (acc, engine), (obj, sha, size) in phases.items():
        require(((acc, engine, "COMMITTED.json"), sha, size) in source_refs,
                "COHORT_COMPLETE does not bind " + acc + "/" + engine)
    return phases, receipts, targets, n

def receipts_and_expected(phases, receipts, targets):
    expected = {}
    totals = Counter()
    phase_rows = []
    for acc in sorted(targets):
        for engine in ENGINES:
            obj, _, _ = phases[acc, engine]
            require(obj["accession"] == acc and obj["engine"] == ENGINES[engine],
                    "Wrong phase source/engine: " + acc + "/" + engine)
            artifacts = {}
            for r in obj["artifacts"]:
                k = refkey(r)
                require(k not in artifacts, "Duplicate phase artifact: " + str(k))
                artifacts[k] = r
            local = [(k, v) for k, v in receipts.items() if k[:2] == (acc, engine)]
            search_shas = []
            count = 0
            for k, (receipt, sha, size) in local:
                require(k in artifacts and artifacts[k]["sha256"] == sha
                        and artifacts[k]["bytes"] == size,
                        "Unbound HMMER receipt: " + str(k))
                require(receipt["status"] == "ACTUAL_HMMER_EXIT_AND_RAW_CHECKPOINT_OBSERVED"
                        and type(receipt["actual_exit_code"]) is int
                        and receipt["actual_exit_code"] == 0
                        and receipt["binary_handle_waited_and_reaped"] is True
                        and isinstance(receipt["binary_identity"], dict),
                        "Invalid HMMER terminal receipt: " + str(k))
                if receipt.get("probe_only"):
                    continue
                require(receipt["no_argument_or_threshold_changes"] is True
                        and len(receipt["raw_outputs"]) > 0
                        and re.fullmatch(r"[0-9a-f]{64}", receipt["query_faa_sha256"])
                        and re.fullmatch(r"[0-9a-f]{64}", receipt["model_file_sha256"]),
                        "Missing search identity or raw references: " + str(k))
                count += 1
                search_shas.append(receipt["model_file_sha256"])
                for raw in receipt["raw_outputs"]:
                    rk = refkey(raw)
                    require(rk in artifacts and rk not in expected
                            and all(artifacts[rk][f] == raw[f] for f in ("path","sha256","bytes")),
                            "Duplicate or unbound HMMER raw output: " + str(rk))
                    expected[rk] = raw
            require(count == obj["typed_scientific_HMMER_searches"] and count > 0,
                    "Wrong HMMER search multiplicity: " + acc + "/" + engine)
            if engine == "DefenseFinder":
                data = json.dumps(sorted(Counter(search_shas).items()), separators=(",", ":")).encode()
                require(hashlib.sha256(data).hexdigest() == DF_MULTISET_SHA,
                        "DefenseFinder independent profile multiset differs: " + acc)
            else:
                require(len(set(search_shas)) == 1,
                        "PADLOC profile mismatch: " + acc)
            calls = obj["model_relative_calls"]
            require(type(calls) is int and calls >= 0, "Invalid phase call count")
            totals[engine] += calls
            totals["hmmer_searches"] += count
            phase_rows.append({"accession": acc, "engine": engine,
                               "typed_hmmer_searches": count, "saved_model_relative_calls": calls})
    require(totals["PADLOC"] == 194 and totals["DefenseFinder"] == 143,
            "Saved model-relative calls differ from prior 194/143 checkpoint")
    return expected, totals, phase_rows

def audit_raw(archive, expected):
    seen = set()
    total_bytes = 0
    with tarfile.open(archive, "r|gz") as tar:
        for m in tar:
            k = key(m.name)
            if k not in expected:
                continue
            require(m.isfile() and k not in seen, "Duplicate/nonfile raw member: " + str(k))
            f = tar.extractfile(m)
            require(f is not None, "Unreadable raw member: " + m.name)
            sha, size, tail = digest(f)
            r = expected[k]
            require(sha == r["sha256"] and size == r["bytes"] and size == m.size,
                    "RAW SHA/size mismatch: " + str(k))
            lines = tail.strip().splitlines()
            require(bool(lines), "Empty HMMER raw output: " + str(k))
            require(lines[-1].strip() == b"# [ok]" if k[1] == "PADLOC"
                    else lines[-1].strip() in (b"[ok]", b"# [ok]"),
                    "HMMER completion footer missing: " + str(k))
            seen.add(k)
            total_bytes += size
    require(seen == set(expected), "Missing HMMER raw outputs: " + str(len(set(expected) - seen)))
    return total_bytes

def main():
    require(len(sys.argv) == 3, "Usage: qa.py <C009 release tar.gz.part0001> <output.json>")
    archive, out = Path(sys.argv[1]), Path(sys.argv[2])
    require(archive.is_file() and archive.stat().st_size == ARCHIVE_SIZE,
            "Pinned archive missing or wrong size")
    with archive.open("rb") as f:
        sha, length, _ = digest(f)
    require(sha == ARCHIVE_SHA, "Pinned archive SHA mismatch")
    print("C009_PINNED_RELEASE_ARCHIVE_VERIFIED", length, flush=True)
    phases, receipts, targets, members = scan_metadata(archive)
    print("C009_PHASES", len(phases), "RECEIPTS", len(receipts), "MEMBERS", members, flush=True)
    expected, totals, rows = receipts_and_expected(phases, receipts, targets)
    print("C009_TYPED_HMMER_SEARCHES", totals["hmmer_searches"],
          "RAW_OUTPUTS", len(expected), flush=True)
    raw_bytes = audit_raw(archive, expected)
    result = {
        "schema": "TREE2_C009_ARCHIVED_RAW_HMMER_FILE_QA_V002",
        "status": "PASS_C009_ARCHIVE_RAW_HMMER_EVIDENCE_NOT_FULL_BIOLOGICAL_QA",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pinned_archive_sha256": sha, "pinned_archive_bytes": length,
        "source_members": members, "selected_accessions": sorted(targets),
        "phase_count": len(phases), "receipt_count": len(receipts),
        "typed_hmmer_searches": totals["hmmer_searches"],
        "raw_files_rehashed": len(expected), "raw_uncompressed_bytes": raw_bytes,
        "stock_model_relative_calls": {"PADLOC": totals["PADLOC"],
                                       "DefenseFinder": totals["DefenseFinder"]},
        "phases": rows,
        "limitations": [
            "Historical WD process and lease closure not established",
            "Original installed HMMER and model/input source bytes not reverified",
            "Not an independent biological interpretation of HMMER profile alignments",
            "Original later targeted QA TSV/JSON not in this frozen release",
            "No cohort ledger promotion or downstream scientific acceptance"
        ],
        "ledger_promoted": False
    }
    require(not out.exists(), "Will not overwrite QA output")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS_C009_ARCHIVED_RAW_HMMER_FILE_QA", flush=True)
    print("C009_STATUS_NOT_PROMOTED", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL_C009_ARCHIVED_RAW_HMMER_FILE_QA", type(exc).__name__, str(exc), file=sys.stderr)
        raise SystemExit(2)
