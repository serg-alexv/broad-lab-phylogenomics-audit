"""Bounded fixtures for stage-neutral observation and fresh symbolic Git refs."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("monitor_v4_source", ROOT / "scripts/prep_activity_collector_v4.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture = ROOT / "work" / ("monitor_v4_source_fixture_" + uuid.uuid4().hex)
fixture.mkdir(parents=True)
def git(*args):
    result = subprocess.run(["git", "-C", str(fixture), *args], capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()
def commit(message):
    git("add", "--", "metadata/")
    git("-c", "user.name=Monitor fixture", "-c", "user.email=monitor-fixture@localhost", "commit", "-m", message)
    return git("rev-parse", "HEAD")
git("init")
(fixture / "metadata").mkdir()
(fixture / "state").mkdir()
n5 = fixture / "metadata/fixture_N5_review.json"
n5.write_text('{"status":"IN_REVIEW","updated_utc":"2026-10-27T00:00:00Z"}', encoding="utf-8")
first_commit = commit("Fixture N5 preparation")
head_path = fixture / ".git/HEAD"
head_bytes, head_mtime = head_path.read_bytes(), head_path.stat().st_mtime_ns
observer = module.Collector(fixture)
first = observer.build()
assert first["latest_source_commit"]["sha"] == first_commit
before_events = len(first["recent_events"])
n5.write_text('{"status":"IN_REVIEW","updated_utc":"2026-10-27T01:00:00Z"}', encoding="utf-8")
second = observer.build()
assert len(second["recent_events"]) == before_events
n5.write_text('{"status":"PASS","updated_utc":"2026-10-27T02:00:00Z"}', encoding="utf-8")
second_commit = commit("Fixture N5 independent review passed")
assert head_path.read_bytes() == head_bytes and head_path.stat().st_mtime_ns == head_mtime
observer.git_at = 0
third = observer.build()
assert third["resolved_git_HEAD"] == second_commit
assert third["latest_source_commit"]["sha"] == second_commit
assert any(e["kind"] == "CONTENT_CHANGED" and e["path"].endswith("fixture_N5_review.json") for e in third["recent_events"])
# A new stage and a deeper gate-linked receipt are discovered without changing source.
n6 = fixture / "metadata/fixture_stage07_alignment_review.json"
n6.write_text('{"status":"SYNTHETIC_SOURCE_PASS"}', encoding="utf-8")
deep_rel = "evidence/future_stage/deeper/review/fixture_receipt.json"
deep = fixture / deep_rel
deep.parent.mkdir(parents=True)
deep.write_text('{"status":"FUTURE_GATE_RECEIPT"}', encoding="utf-8")
(fixture / "state/preparation_gates_v2.json").write_text(json.dumps({"mode": "FUTURE_STAGE", "code_frozen": False, "gates": [{"evidence_path": deep_rel}]}), encoding="utf-8")
fourth = observer.build()
assert "metadata/fixture_stage07_alignment_review.json" in {row["path"] for row in fourth["artifacts"]}
assert deep_rel in {row["path"] for row in fourth["artifacts"]}
# Baseline scans cannot evict newer review events merely due to traversal order.
for number in range(60):
    old = fixture / "metadata" / ("fixture_old_" + str(number) + ".json")
    old.write_text('{"status":"OLD_BASELINE"}', encoding="utf-8")
    os.utime(old, (1700000000, 1700000000))
fifth = observer.build()
assert any(e["path"] == deep_rel for e in fifth["recent_events"])
report = {"status": "PASS_V4_MONITOR_ONLY", "N5_and_future_stage_artifacts_auto_discovered": True, "gate_linked_deeper_receipt_discovered": True, "symbolic_HEAD_bytes_and_mtime_unchanged_while_ref_advanced": True, "fresh_git_query_detected_new_ref": True, "timestamp_only_JSON_rewrite_not_progress": True, "newest_events_preserved_across_large_baseline_scan": True, "monitor_collector_or_scientific_worker_launched": False, "fixture": str(fixture.relative_to(ROOT))}
(fixture / "test_receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
