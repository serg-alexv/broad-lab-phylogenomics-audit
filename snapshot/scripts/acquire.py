#!/usr/bin/env python3
"""Single-worker, receipt-verified NCBI acquisition. Biology remains NOT_RUN.

Network interruptions resume at accession boundaries; byte ranges are reused only
when the server validates them. The isolated --self-test uses loopback fixtures.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.server
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
import uuid
import zipfile

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEFAULT_ROOT / "tools" / "python_lib"))
import requests

ACCESSION = re.compile(r"GC[AF]_\d{9}\.\d+\Z")
ANNOTATIONS = ["GENOME_FASTA", "PROT_FASTA", "GENOME_GFF", "SEQUENCE_REPORT"]
API = "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/{accession}/download"
MAX_BYTES = 1024 ** 3
MIN_FREE = 20 * 1024 ** 3


def utc():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class StopRequested(Exception):
    pass


class SequenceQCError(ValueError):
    def __init__(self, message, stats=None, evidence=None):
        super().__init__(message)
        self.stats = stats
        self.evidence = evidence


def process_creation_identity():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class FILETIME(ctypes.Structure):
            _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(FILETIME)] * 4
        creation, exited, kern, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not kernel.GetProcessTimes(kernel.GetCurrentProcess(), ctypes.byref(creation), ctypes.byref(exited), ctypes.byref(kern), ctypes.byref(user)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {"pid": os.getpid(), "windows_creation_filetime_100ns": (creation.high << 32) | creation.low}
    stat = Path("/proc/self/stat").read_text()
    # command in parentheses may contain spaces; starttime is field 22.
    return {"pid": os.getpid(), "linux_starttime_ticks": int(stat.rsplit(")", 1)[1].split()[19]),
            "linux_boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}


def stop_check(root):
    if (root / "state" / "STOP").exists():
        raise StopRequested("state/STOP exists")
    if shutil.disk_usage(root).free < MIN_FREE:
        raise StopRequested("Less than 20 GiB free on project volume")


@contextlib.contextmanager
def process_lock(root, run_id):
    path = root / "state" / "acquire.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    f = path.open("a+b")
    try:
        if path.stat().st_size == 0:
            f.write(b" ")
            f.flush()
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        atomic_json(root / "state" / "acquire_owner.json", {
            "run_id": run_id, "pid": os.getpid(), "started_utc": utc(),
            "process_creation_identity": process_creation_identity(),
            "hostname": __import__("socket").gethostname(),
            "python": sys.executable, "script_sha256": sha(__file__),
            "lock_semantics": "OS exclusive byte lock; owner JSON alone is not liveness proof",
        })
        yield
    finally:
        f.close()  # kernel releases lock even after forced termination


def checked_zip(path, accession):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP CRC validation failed")
        total = 0
        path_names = set()
        for member in z.infolist():
            p = PurePosixPath(member.filename)
            if p.is_absolute() or ".." in p.parts or "\\" in member.filename or ":" in member.filename:
                raise ValueError("Unsafe package path")
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP symlink refused")
            folded = member.filename.casefold()
            if folded in path_names:
                raise ValueError("Duplicate/case-colliding ZIP member")
            path_names.add(folded)
            total += member.file_size
            if total > MAX_BYTES:
                raise ValueError("Unpacked package exceeds 1 GiB")
        reports = [n for n in z.namelist() if n.endswith("/assembly_data_report.jsonl")]
        if len(reports) != 1:
            raise ValueError("Missing/ambiguous assembly_data_report.jsonl")
        rows = [json.loads(x) for x in z.read(reports[0]).decode("utf-8").splitlines() if x.strip()]
        matches = [r for r in rows if r.get("accession") == accession]
        if len(matches) != 1:
            raise ValueError("Package report does not identify requested versioned accession")
        names = z.namelist()
        for suffix in (".fna", "sequence_report.jsonl"):
            if not any(n.endswith(suffix) for n in names):
                raise ValueError("Package missing required " + suffix)
        return matches[0]


def genome_stats(stage, record, report):
    seen = set()
    total = ambiguous = contigs = 0
    alphabet = set(b"ACGTRYSWKMBDHVN")
    for path in sorted(stage.rglob("*.fna")):
        active = False
        seq_length = 0
        with path.open("rb") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith(b">"):
                    if active and not seq_length:
                        raise ValueError("Empty FASTA record")
                    ident = line[1:].split()[0].decode("ascii")
                    if not ident or ident in seen:
                        raise ValueError("Duplicate/empty FASTA identifier")
                    seen.add(ident)
                    contigs += 1
                    active = True
                    seq_length = 0
                else:
                    if not active:
                        raise ValueError("Sequence precedes FASTA header")
                    seq = line.upper()
                    if set(seq) - alphabet:
                        raise ValueError("Invalid genomic DNA alphabet")
                    total += len(seq)
                    seq_length += len(seq)
                    ambiguous += sum(c not in b"ACGT" for c in seq)
            if active and not seq_length:
                raise ValueError("Empty final FASTA record")
    if not total:
        raise ValueError("No genomic FASTA bases")
    expected_values = []
    for obj in (record, record.get("assembly_stats", {}), record.get("assemblyStats", {}), report.get("assemblyStats", {}), report.get("assembly_stats", {})):
        for key in ("total_sequence_length", "totalSequenceLength", "genome_size", "genome_length"):
            if obj.get(key) is not None:
                expected_values.append(int(obj[key]))
    if not expected_values:
        raise ValueError("No source total sequence length to verify genomic FASTA")
    if any(x != total for x in expected_values):
        raise ValueError(f"FASTA length {total} != source totals {expected_values}")
    result = {"total_sequence_length": total, "contigs": contigs,
            "ambiguous_bases": ambiguous, "ambiguous_fraction": ambiguous / total,
            "source_lengths": expected_values, "fasta_validation": "PASS"}
    if ambiguous / total > .01:
        result["fasta_validation"] = "FAIL_AMBIGUITY_GT_1_PERCENT"
        raise SequenceQCError("Genomic FASTA ambiguous fraction exceeds 1%", result)
    return result


def verified_receipt(folder, accession):
    receipt = folder / "acquisition_receipt.json"
    if not receipt.exists():
        return None
    try:
        r = json.loads(receipt.read_text(encoding="utf-8"))
        if r["accession"] != accession or r["acquisition_status"] != "PASS":
            return None
        for row in r["files"]:
            rel = PurePosixPath(row["path"])
            if rel.is_absolute() or ".." in rel.parts:
                return None
            p = folder.joinpath(*rel.parts)
            if p.stat().st_size != row["bytes"] or sha(p) != row["sha256"]:
                return None
        actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != "acquisition_receipt.json"}
        if actual != {r["path"] for r in r["files"]}:
            return None
        return r
    except (OSError, ValueError, KeyError, TypeError):
        return None


def fetch(root, accession, session, endpoint, retries):
    package_dir = root / "work" / "packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    committed = package_dir / (accession + ".zip")
    if committed.exists():
        checked_zip(committed, accession)
        return committed
    part = package_dir / (accession + ".zip.part")
    http_state = package_dir / (accession + ".http.json")
    last = None
    for attempt in range(retries):
        stop_check(root)
        try:
            old = json.loads(http_state.read_text()) if http_state.exists() else {}
            start = part.stat().st_size if part.exists() else 0
            headers = {"Accept": "application/zip"}
            if start and old.get("etag"):
                headers.update({"Range": f"bytes={start}-", "If-Range": old["etag"]})
            url = endpoint.format(accession=accession)
            with session.get(url, params={"include_annotation_type": ANNOTATIONS}, headers=headers,
                             timeout=(20, 60), stream=True, allow_redirects=False) as response:
                response.raise_for_status()
                append = (start > 0 and response.status_code == 206 and
                          response.headers.get("Content-Range", "").startswith(f"bytes {start}-") and
                          response.headers.get("ETag") == old.get("etag"))
                if response.status_code == 206 and not append:
                    raise ValueError("Unvalidated HTTP byte range")
                atomic_json(http_state, {"url": url, "request_url": response.url,
                            "query_parameters": {"include_annotation_type": ANNOTATIONS},
                            "request_headers": {**headers, "User-Agent": session.headers["User-Agent"]},
                            "response_headers": {k: response.headers[k] for k in
                                ("Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Range") if k in response.headers},
                            "etag": response.headers.get("ETag"),
                            "started_utc": utc(), "http_status": response.status_code})
                count = start if append else 0
                with part.open("ab" if append else "wb") as f:
                    for chunk in response.iter_content(1024 * 256):
                        if not chunk:
                            continue
                        stop_check(root)
                        count += len(chunk)
                        if count > MAX_BYTES:
                            raise ValueError("Compressed package exceeds 1 GiB")
                        f.write(chunk)
                        f.flush()
                    os.fsync(f.fileno())
                checked_zip(part, accession)
                os.replace(part, committed)
                return committed
        except StopRequested:
            raise
        except (requests.RequestException, OSError, ValueError, zipfile.BadZipFile) as exc:
            last = exc
            # A completed corrupt package cannot safely resume; preserve evidence.
            if isinstance(exc, (zipfile.BadZipFile, ValueError)) and part.exists():
                os.replace(part, part.with_name(part.name + ".rejected-" + uuid.uuid4().hex[:8]))
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Download failed after {retries} attempts: {last}")


def acquire_one(root, record, session, endpoint, retries, run_id, panel_sha256):
    accession = record["accession"]
    if not ACCESSION.fullmatch(accession):
        raise ValueError("Versioned GCA/GCF accession required")
    destination = root / "raw" / accession
    old = verified_receipt(destination, accession)
    if old is not None:
        return {"accession": accession, "action": "VERIFIED_SKIP", "receipt_sha256": sha(destination / "acquisition_receipt.json")}
    stop_check(root)
    package = fetch(root, accession, session, endpoint, retries)
    report = checked_zip(package, accession)
    stage = root / "raw" / (".staging-" + accession + "-" + run_id)
    stage.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(package) as z:
        for item in z.infolist():
            stop_check(root)
            if item.is_dir():
                continue
            path = stage.joinpath(*PurePosixPath(item.filename).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as src, path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
                dst.flush()
                os.fsync(dst.fileno())
    try:
        qc = genome_stats(stage, record, report)
    except ValueError as exc:
        rejection = root / "work" / "rejected" / (accession + "-" + run_id)
        rejection.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(stage / "rejection_receipt.json", {
            "accession": accession, "run_id": run_id, "rejected_utc": utc(),
            "acquisition_status": "FAIL_SEQUENCE_QC", "error": str(exc),
            "sequence_qc": getattr(exc, "stats", None), "metadata_record": record,
            "script_sha256": sha(__file__), "panel_sha256": panel_sha256,
            "package_sha256": sha(package),
            "files": [{"path": p.relative_to(stage).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
                      for p in sorted(stage.rglob("*")) if p.is_file()]})
        os.replace(stage, rejection)
        raise SequenceQCError(str(exc), getattr(exc, "stats", None), str(rejection)) from exc
    files = [{"path": p.relative_to(stage).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
             for p in sorted(stage.rglob("*")) if p.is_file()]
    receipt = {"schema": "tree2-acquisition-v1", "accession": accession,
               "run_id": run_id, "completed_utc": utc(), "acquisition_status": "PASS",
               "package_sha256": sha(package), "metadata_record": record,
               "source_url": endpoint.format(accession=accession),
               "requested_annotations": ANNOTATIONS,
               "http_receipt": json.loads((root / "work" / "packages" / (accession + ".http.json")).read_text())
                   if (root / "work" / "packages" / (accession + ".http.json")).exists() else None,
               "script_sha256": sha(__file__), "panel_sha256": panel_sha256,
               "sequence_qc": qc, "files": files,
               "source_annotation": {
                   "protein_fasta_present": any(p.name.endswith(".faa") for p in stage.rglob("*")),
                   "gff_present": any(p.name.endswith(".gff") for p in stage.rglob("*")),
                   "completeness": "AVAILABLE" if any(p.name.endswith(".faa") for p in stage.rglob("*")) and any(p.name.endswith(".gff") for p in stage.rglob("*")) else "INCOMPLETE"},
               "annotation_status": "NOT_RUN",
               "genome_quality_status": "NOT_RUN", "taxonomy_sequence_validation": "NOT_RUN",
               "marker_status": "NOT_RUN", "padloc_status": "NOT_RUN", "defensefinder_status": "NOT_RUN",
               "defence_binary": None,
               "note": "Acquisition validation is not biological completeness/contamination or defence QC."}
    atomic_json(stage / "acquisition_receipt.json", receipt)
    if not verified_receipt(stage, accession):
        raise ValueError("Staged receipt verification failed")
    if destination.exists():
        quarantine = root / "work" / "quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        os.replace(destination, quarantine / (accession + "-" + run_id))
    os.replace(stage, destination)
    return {"accession": accession, "action": "ACQUIRED", "receipt_sha256": sha(destination / "acquisition_receipt.json"), "sequence_qc": qc}


def run(args):
    hostname = __import__("socket").gethostname()
    if args.test_mode != bool(args.test_endpoint):
        raise ValueError("--test-mode and --test-endpoint must be used together; fixtures never use the production endpoint")
    if not args.test_mode and hostname.casefold() != "wd":
        raise RuntimeError(f"Production acquisition is WD-only; current host is {hostname}")
    root = Path(args.root).resolve()
    for p in ("state", "raw", "logs", "work"):
        (root / p).mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    endpoint = API
    if args.test_endpoint:
        from urllib.parse import urlparse
        if not args.test_mode or urlparse(args.test_endpoint).hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("Fixture endpoint requires --test-mode and loopback host")
        endpoint = args.test_endpoint
    panel = Path(args.panel) if args.panel else root / "metadata" / "provisional_panel.json"
    data = json.loads(panel.read_text(encoding="utf-8-sig"))
    panel_sha256 = sha(panel)
    if not isinstance(data, list):
        raise ValueError("Panel must be a JSON list")
    selected = data[:args.limit] if args.limit else data
    results = []
    status = "FAILED"
    error = None
    try:
        with process_lock(root, run_id):
            with requests.Session() as session:
                session.headers["User-Agent"] = "Tree2-WD-local-research/1.0"
                for record in selected:
                    stop_check(root)
                    try:
                        result = acquire_one(root, record, session, endpoint, args.retries, run_id, panel_sha256)
                    except StopRequested:
                        raise
                    except Exception as exc:
                        result = {"accession": record.get("accession"), "action": "FAILED", "error": repr(exc)}
                        if getattr(exc, "evidence", None):
                            result["rejection_evidence"] = exc.evidence
                    results.append(result)
                    print(json.dumps(result, ensure_ascii=False), flush=True)
                    atomic_json(root / "state" / "acquisition_progress.json", {"run_id": run_id, "updated_utc": utc(), "results": results})
                status = "COMPLETE" if all(x["action"] != "FAILED" for x in results) else "PARTIAL_FAILURE"
    except (StopRequested, KeyboardInterrupt) as exc:
        status, error = "STOPPED", str(exc)
    except Exception as exc:
        error = repr(exc)
    finally:
        receipt = {"run_id": run_id, "pid": os.getpid(), "ended_utc": utc(), "status": status,
                   "process_creation_identity": process_creation_identity(),
                   "error": error, "results": results, "process_lock_released": True,
                   "selected_count": len(selected), "panel_sha256": panel_sha256}
        atomic_json(root / "logs" / ("acquisition_exit_" + run_id + ".json"), receipt)
        atomic_json(root / "state" / "acquisition_last_exit.json", receipt)
    return 0 if status == "COMPLETE" else 2


def self_test():
    base = DEFAULT_ROOT / "work" / ("acquire_selftest_" + uuid.uuid4().hex[:8])
    root = base / "project"
    (root / "metadata").mkdir(parents=True)
    accession = "GCF_000000001.1"
    sequence = b"ACGT" * 100000
    package = io.BytesIO()
    prefix = "ncbi_dataset/data/"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_STORED) as z:
        z.writestr(prefix + "assembly_data_report.jsonl", json.dumps({"accession": accession, "assemblyStats": {"totalSequenceLength": len(sequence)}}) + "\n")
        z.writestr(prefix + accession + "/genomic.fna", b">fixture_contig\n" + sequence + b"\n")
        z.writestr(prefix + accession + "/protein.faa", ">fixture_gene\nMKKL\n")
        z.writestr(prefix + accession + "/genomic.gff", "##gff-version 3\n")
        z.writestr(prefix + accession + "/sequence_report.jsonl", '{"accession":"fixture_contig","length":400000}\n')
    payload = package.getvalue()
    requests_seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            start = int(self.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0])
            requests_seen.append({"range": start})
            self.send_response(206 if start else 200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("ETag", '"fixture-v1"')
            self.send_header("Content-Length", str(len(payload) - start))
            if start:
                self.send_header("Content-Range", f"bytes {start}-{len(payload)-1}/{len(payload)}")
            self.end_headers()
            try:
                for i in range(start, len(payload), 16384):
                    self.wfile.write(payload[i:i + 16384])
                    self.wfile.flush()
                    time.sleep(.04)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    atomic_json(root / "metadata" / "provisional_panel.json", [{"accession": accession, "total_sequence_length": len(sequence)}])
    cmd = [sys.executable, str(Path(__file__).resolve()), "--root", str(root), "--limit", "1", "--test-mode", "--test-endpoint", f"http://127.0.0.1:{server.server_address[1]}/{{accession}}"]
    output = base / "forced_stop.log"
    with output.open("w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        partial = root / "work" / "packages" / (accession + ".zip.part")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not (partial.exists() and partial.stat().st_size > 0):
            if proc.poll() is not None:
                raise AssertionError("Fixture child exited before partial download")
            time.sleep(.05)
        assert partial.exists() and partial.stat().st_size > 0
        proc.kill()
        killed_code = proc.wait(timeout=10)
    assert not (root / "raw" / accession).exists(), "Interrupted acquisition published output"
    resumed = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    (base / "resume.log").write_text(resumed.stdout + resumed.stderr, encoding="utf-8")
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    receipt_path = root / "raw" / accession / "acquisition_receipt.json"
    first_sha = sha(receipt_path)
    count_before_skip = len(requests_seen)
    skipped = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert skipped.returncode == 0 and "VERIFIED_SKIP" in skipped.stdout, skipped.stdout + skipped.stderr
    assert sha(receipt_path) == first_sha and len(requests_seen) == count_before_skip
    # A corrupted committed file must fail receipt verification and be quarantined.
    genomic = next((root / "raw" / accession).rglob("*.fna"))
    with genomic.open("ab") as f:
        f.write(b"N\n")
    repaired = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert repaired.returncode == 0 and '"action": "ACQUIRED"' in repaired.stdout
    assert verified_receipt(root / "raw" / accession, accession)
    assert len(list((root / "work" / "quarantine").iterdir())) == 1
    assert len(requests_seen) == count_before_skip, "Validated local ZIP should repair without download"
    # A deliberate stop file must prevent network activity and yield a stop receipt.
    (root / "state" / "STOP").write_text("fixture stop\n")
    stopped = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert stopped.returncode == 2
    assert json.loads((root / "state" / "acquisition_last_exit.json").read_text())["status"] == "STOPPED"
    assert len(requests_seen) == count_before_skip

    def variant_project(name, ambiguous):
        project = base / name
        (project / "metadata").mkdir(parents=True)
        atomic_json(project / "metadata" / "provisional_panel.json", [{"accession": accession, "total_sequence_length": len(sequence)}])
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            z.writestr(prefix + "assembly_data_report.jsonl", json.dumps({"accession": accession, "assemblyStats": {"totalSequenceLength": len(sequence)}}) + "\n")
            seq = (b"N" * 8000 + sequence[8000:]) if ambiguous else sequence
            z.writestr(prefix + accession + "/genomic.fna", b">fixture_contig\n" + seq + b"\n")
            z.writestr(prefix + accession + "/sequence_report.jsonl", '{"accession":"fixture_contig","length":400000}\n')
        variant_cmd = cmd.copy()
        variant_cmd[variant_cmd.index("--root") + 1] = str(project)
        return project, buf.getvalue(), variant_cmd

    unannotated_root, payload, unannotated_cmd = variant_project("unannotated_project", False)
    unannotated = subprocess.run(unannotated_cmd, capture_output=True, text=True, timeout=30)
    assert unannotated.returncode == 0, unannotated.stdout + unannotated.stderr
    unannotated_receipt = verified_receipt(unannotated_root / "raw" / accession, accession)
    assert unannotated_receipt["source_annotation"]["completeness"] == "INCOMPLETE"
    assert unannotated_receipt["annotation_status"] == "NOT_RUN"

    ambiguous_root, payload, ambiguous_cmd = variant_project("ambiguous_project", True)
    ambiguous_result = subprocess.run(ambiguous_cmd, capture_output=True, text=True, timeout=30)
    assert ambiguous_result.returncode == 2, ambiguous_result.stdout + ambiguous_result.stderr
    assert not (ambiguous_root / "raw" / accession).exists()
    rejection_path = next((ambiguous_root / "work" / "rejected").rglob("rejection_receipt.json"))
    rejection = json.loads(rejection_path.read_text())
    assert rejection["sequence_qc"]["ambiguous_fraction"] == .02
    assert rejection["acquisition_status"] == "FAIL_SEQUENCE_QC"
    server.shutdown()
    summary = {"status": "PASS", "completed_utc": utc(), "fixture_directory": str(base),
               "forced_kill_returncode": killed_code, "partial_not_published": True,
               "resume_validated": True, "verified_skip_unchanged_receipt": True,
               "corrupted_committed_file_detected_and_quarantined": True,
               "stop_file_prevented_network": True, "http_requests": requests_seen,
               "unannotated_genome_acquired_annotation_not_run": True,
               "ambiguity_gt_1pct_rejected_with_original_evidence": True,
               "fixture_only": True, "no_biological_claims": True}
    atomic_json(base / "selftest_receipt.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(DEFAULT_ROOT))
    p.add_argument("--panel")
    p.add_argument("--limit", type=int, default=10, help="0 means full panel")
    p.add_argument("--retries", type=int, default=4)
    p.add_argument("--test-mode", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--test-endpoint", help=argparse.SUPPRESS)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.limit < 0 or args.retries < 1:
        p.error("limit must be nonnegative and retries positive")
    return self_test() if args.self_test else run(args)


if __name__ == "__main__":
    raise SystemExit(main())
