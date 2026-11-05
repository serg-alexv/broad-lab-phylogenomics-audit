"""Read-only preparation observer. Writes only its new monitor sidecars, never science.

No scientific imports, WSL/runtime/model probes, process launches, or admission changes.
Content changes count as events; timestamp-only JSON rewrites do not.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

UTC = dt.timezone.utc
SOURCE_CHECKPOINT = "checkpoints/N1_SOURCE_HELD_20261027T084045Z/receipt.json"
SOURCE_CHECKPOINT_SHA256 = "081b7e96114c97f48ccb8e7192d1f98d70806b2ef5b99c2bd30ab4e7aba6e229"
IGNORED_KEYS = {"updated_utc", "at_utc", "created_utc", "prepared_utc", "observed_utc", "heartbeat_utc", "last_seen_utc", "timestamp", "timestamp_utc"}
DEFAULT_GATES = [
    {"id": "scientific_review", "label": "Independent final scientific / ABI source review", "status": "PENDING", "detail": "next_qc review of the frozen N1 tuple"},
    {"id": "root_review", "label": "Root final lifecycle / source review", "status": "PENDING", "detail": "Combined frozen source and input contract"},
    {"id": "prelaunch", "label": "Separately authorized source / transport / resource prelaunch", "status": "NOT_STARTED", "detail": "Fresh resource and exclusivity evidence required"},
    {"id": "ready", "label": "Explicit Root scientific Ready, then launch", "status": "NOT_GRANTED", "detail": "Launch timing unknown until review gates complete"},
]

def utcnow():
    return dt.datetime.now(UTC).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items() if k not in IGNORED_KEYS and not k.endswith("_heartbeat_utc")}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None

def atomic_json(path, value):
    part = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    with part.open("w", encoding="utf-8", newline="\n") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    # Windows readers/AV may temporarily deny replace. Keep the same complete
    # candidate and retry finitely; never truncate the last committed snapshot.
    for attempt in range(30):
        try:
            os.replace(part, path)
            return
        except PermissionError:
            if attempt == 29:
                raise
            time.sleep(0.05)

def checkpoint_binding(root, artifacts, expected_receipt_sha256=SOURCE_CHECKPOINT_SHA256):
    """Keep the explicit source freeze separate from later admission checkpoints.

    The source receipt is pinned, not selected by directory modification time.
    A later admission receipt is contextual evidence, never an execution result.
    """
    source = read_json(Path(root) / SOURCE_CHECKPOINT) or {}
    source_row = artifacts.get(SOURCE_CHECKPOINT, {})
    binding = source.get("source_manifest", {})
    manifest = artifacts.get(binding.get("path"), {})
    exact_receipt = source_row.get("sha256") == expected_receipt_sha256
    source_kind = source.get("status") == "N1_HELD_SOURCE_CHECKPOINT_NO_SCIENTIFIC_GRANT"
    bound = bool(exact_receipt and source_kind and binding.get("sha256") and binding.get("sha256") == manifest.get("sha256"))
    admissions = []
    for rel, row in artifacts.items():
        if rel.startswith("checkpoints/N1_ADMITTED_") and rel.endswith("/receipt.json"):
            receipt = read_json(Path(root) / rel) or {}
            if receipt.get("status") == "N1_ADMISSION_CHECKPOINT_NOT_EXECUTION_RESULT":
                admissions.append({"path": rel, "sha256": row.get("sha256"), "at_utc": row.get("meaningful_utc", row.get("mtime_utc")), "status": receipt["status"]})
    admission = max(admissions, key=lambda row: row.get("at_utc") or "", default=None)
    return {"source_checkpoint": SOURCE_CHECKPOINT, "source_checkpoint_sha256": source_row.get("sha256"), "source_checkpoint_exact": exact_receipt, "manifest_matches": bound, "admission_checkpoint": admission}

class Collector:
    def __init__(self, root, output=None, watch_paths=None):
        self.root = Path(root).resolve()
        self.output = Path(output or self.root / "state" / "monitor_v3").resolve()
        self.output.relative_to(self.root / "state")
        self.output.mkdir(parents=True, exist_ok=True)
        self.watch_paths = watch_paths
        self.cache = {}
        self.events = []
        self.event_path = self.output / "events.jsonl"
        self.state_path = self.output / "preparation_activity.json"
        self.previous = read_json(self.state_path) or {}
        self.last_commit = self.previous.get("latest_source_commit")
        self.git_at = 0
        self.sequence = int(self.previous.get("sequence", 0))
        self.errors = []
        # The previous file list is a resume cache, not evidence of new activity.
        for row in self.previous.get("artifacts", []):
            self.cache[row["path"]] = row
        self.events = self.previous.get("recent_events", [])[-50:]

    def paths(self):
        if self.watch_paths is not None:
            return [self.root / p for p in self.watch_paths]
        found = set()
        patterns = {
            "metadata": ["*N1*.json", "checkm2_accepted_method_result_registry_v001.json", "checkm2_S1R2_finalizer_closed_checkpoint.json"],
            "scripts": ["*N1*.py", "*N1*.sh"],
            "docs": ["*N1*.md"],
            "evidence/checkm2_phase_separated_N1": ["*.json"],
            "state": ["preparation_gates_v2.json"],
        }
        for folder, globs in patterns.items():
            for pattern in globs:
                found.update((self.root / folder).glob(pattern))
        found.update((self.root / "checkpoints").glob("N1*/receipt.json"))
        return sorted(found)

    def record_event(self, row, kind):
        event = {"observed_utc": utcnow(), "artifact_utc": row["mtime_utc"], "path": row["path"], "kind": kind, "sha256": row["sha256"], "status": row.get("status", "")}
        self.events.append(event)
        self.events = self.events[-50:]
        with self.event_path.open("a", encoding="utf-8", newline="\n") as out:
            out.write(json.dumps(event, ensure_ascii=False) + "\n")

    def scan(self):
        self.errors = []
        for path in self.paths():
            try:
                path.resolve().relative_to(self.root)
                rel = path.relative_to(self.root).as_posix()
                st = path.stat()
                old = self.cache.get(rel)
                if old and old.get("mtime_ns") == st.st_mtime_ns and old.get("bytes") == st.st_size:
                    continue
                raw = path.read_bytes()
                value = None
                if path.suffix.lower() == ".json":
                    value = json.loads(raw.decode("utf-8-sig"))
                    fingerprint = sha(json.dumps(semantic(value), sort_keys=True, separators=(",", ":")).encode())
                else:
                    fingerprint = sha(raw)
                modified = dt.datetime.fromtimestamp(st.st_mtime, UTC).isoformat()
                semantic_at = old.get("meaningful_utc", old.get("mtime_utc")) if old and old.get("semantic_sha256") == fingerprint else modified
                row = {"path": rel, "bytes": len(raw), "mtime_ns": st.st_mtime_ns, "mtime_utc": modified, "meaningful_utc": semantic_at, "sha256": sha(raw), "semantic_sha256": fingerprint, "status": str(value.get("status", "")) if isinstance(value, dict) else ""}
                self.cache[rel] = row
                if old is not None and old.get("semantic_sha256") != fingerprint:
                    self.record_event(row, "CONTENT_CHANGED")
                elif old is None:
                    self.record_event(row, "BASELINE_ARTIFACT_OBSERVED")
            except (OSError, ValueError) as exc:
                self.errors.append(str(path.name) + ": " + str(exc))

    def git_commit(self):
        if time.monotonic() - self.git_at < 15:
            return self.last_commit
        self.git_at = time.monotonic()
        try:
            paths = ["metadata/*N1*.json", "scripts/*N1*.py", "scripts/*N1*.sh", "docs/*N1*.md", "checkpoints/N1*/receipt.json", "evidence/checkm2_phase_separated_N1/*.json"]
            result = subprocess.run(["git", "-C", str(self.root), "log", "-1", "--format=%H%x00%cI%x00%s", "--", *paths], capture_output=True, text=True, timeout=3, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode == 0 and result.stdout.strip():
                commit, at, subject = result.stdout.strip().split("\0", 2)
                self.last_commit = {"sha": commit, "at_utc": dt.datetime.fromisoformat(at).astimezone(UTC).isoformat(), "subject": subject}
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            self.errors.append("Local source commit metadata unavailable: " + str(exc))
        return self.last_commit

    def receipt(self, rel):
        value = read_json(self.root / rel)
        row = self.cache.get(rel)
        if not isinstance(value, dict):
            return {"path": rel, "status": "NOT_FOUND_OR_UNREADABLE", "available": False}
        return {"path": rel, "status": value.get("status", value.get("scope", "RECORDED")), "available": True, "sha256": row.get("sha256") if row else None, "data": value}

    def build(self):
        self.scan()
        gate_path = "state/preparation_gates_v2.json"
        gate = read_json(self.root / gate_path) or {}
        checklist = []
        receipts = [
            ("method", "S1R2 method estimates and closure", "metadata/checkm2_S1R2_finalizer_closed_checkpoint.json"),
            ("novelty", "N1 novelty / one-candidate queue review", "metadata/checkm2_N1_novelty_queue_review_v003.json"),
            ("ops", "OPS interface component", "metadata/checkm2_phase_separated_OPS_component_HELD_N1_v002.json"),
            ("artifacts", "Full-field artifact handshake fixtures", "metadata/checkm2_phase_separated_artifact_component_N1.json"),
            ("fixtures", "Six pure source fixture groups", "metadata/checkm2_phase_separated_source_fixtures_N1.json"),
            ("frozen", "Combined frozen source tuple", "metadata/checkm2_phase_separated_implementation_N1_v002.json"),
        ]
        for key, label, rel in receipts:
            receipt = self.receipt(rel)
            entry = {"id": key, "label": label, "status": receipt["status"], "evidence_path": rel, "sha256": receipt.get("sha256")}
            if key == "frozen":
                sources = receipt.get("data", {}).get("sources", [])
                entry["detail"] = str(len(sources)) + " bound source rows; source freeze does not grant scientific execution"
            checklist.append(entry)
        checkpoints = checkpoint_binding(self.root, self.cache)
        bound_ok = checkpoints["manifest_matches"]
        commit = self.git_commit()
        # Timestamp-only JSON updates keep the previous semantic event time.
        source_rows = [row for row in self.cache.values() if not row["path"].startswith("state/")]
        latest = max(source_rows, key=lambda r: r.get("meaningful_utc", r["mtime_utc"]), default=None)
        meaningful = {"artifact_utc": latest.get("meaningful_utc", latest["mtime_utc"]), "kind": "CONTENT_BOUND_ARTIFACT", "path": latest["path"], "sha256": latest["sha256"]} if latest else None
        if commit and (not meaningful or commit["at_utc"] > meaningful["artifact_utc"]):
            meaningful = {"artifact_utc": commit["at_utc"], "kind": "LOCAL_SOURCE_COMMIT", "path": commit["sha"][:12] + " " + commit["subject"]}
        self.sequence += 1
        return {
            "schema": "TREE2_PREPARATION_ACTIVITY_V3", "project": self.root.name,
            "updated_utc": utcnow(), "collector_pid": os.getpid(), "sequence": self.sequence,
            "mode": gate.get("mode", "N1 SOURCE PREPARATION / INDEPENDENT REVIEW"),
            "code_frozen": gate.get("code_frozen", bound_ok),
            "code_frozen_evidence": checkpoints["source_checkpoint"], "code_frozen_manifest_matches": bound_ok,
            "source_checkpoint_exact": checkpoints["source_checkpoint_exact"], "source_checkpoint_sha256": checkpoints["source_checkpoint_sha256"],
            "admission_checkpoint": checkpoints["admission_checkpoint"],
            "detail": gate.get("detail", "Fresh Streptococcus canis GCF_900636575.1 control; source-only preparation, no scientific launch grant."),
            "checklist": checklist, "remaining_gates": gate.get("gates", DEFAULT_GATES),
            "gate_evidence_path": gate_path if gate else None,
            "gate_updated_utc": gate.get("updated_utc"),
            "latest_meaningful_change": meaningful, "latest_source_commit": commit,
            "recent_events": sorted(self.events, key=lambda e: e["artifact_utc"], reverse=True)[:50],
            "artifacts": list(self.cache.values()), "read_errors": self.errors,
            "notice": "Observer refresh is not work progress. Content changes and local source commits are evidence of preparation activity only. No percent or launch ETA is inferred."
        }

    def run_once(self):
        snapshot = self.build()
        atomic_json(self.state_path, snapshot)
        return snapshot

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--interval", type=float, default=4)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not 3 <= args.interval <= 60:
        parser.error("interval must be 3 to 60 seconds")
    observer = Collector(args.project_root)
    owner = {"pid": os.getpid(), "started_utc": utcnow(), "script": str(Path(__file__).resolve()), "role": "READ_ONLY_PREPARATION_OBSERVER_NOT_SCIENTIFIC_WORKER"}
    atomic_json(observer.output / "collector_owner.json", owner)
    stopping = False
    def stop(_sig, _frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    failure = None
    try:
        while not stopping:
            try:
                snapshot = observer.run_once()
            except PermissionError as exc:
                # Optional display publication must not permanently lose this
                # observer because one atomic rename window was unavailable.
                print(json.dumps({"status": "OPTIONAL_PUBLICATION_RETRY", "at_utc": utcnow(), "exception": repr(exc)}), flush=True)
                if args.once:
                    raise
                time.sleep(args.interval)
                continue
            if args.once:
                print(json.dumps({k: snapshot[k] for k in ("updated_utc", "mode", "code_frozen", "latest_meaningful_change", "remaining_gates")}))
                break
            time.sleep(args.interval)
    except BaseException as exc:
        failure = repr(exc)
        raise
    finally:
        atomic_json(observer.output / "collector_exit.json", {**owner, "ended_utc": utcnow(), "status": "OBSERVER_FAILED" if failure else "OBSERVER_EXITED", "exception": failure, "native_exit_code": "UNKNOWN_UNLESS_SEPARATELY_OBSERVED"})

if __name__ == "__main__":
    main()
