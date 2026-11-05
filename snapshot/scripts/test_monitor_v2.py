"""Bounded monitor-only fixture; never changes scientific inputs or receipts."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tree2_observer", ROOT / "scripts/prep_activity_collector_v2.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture = ROOT / "state/monitor_v2" / ("fixture_" + uuid.uuid4().hex)
fixture.mkdir(parents=True)
receipt = fixture / "fixture_review.json"
relative = receipt.relative_to(ROOT).as_posix()
receipt.write_text(json.dumps({"status": "IN_REVIEW", "updated_utc": "2026-10-27T00:00:00Z"}), encoding="utf-8")
observer = module.Collector(ROOT, fixture / "observed", [relative])
observer.git_at = float("inf")
first = observer.run_once()
assert len(first["recent_events"]) == 1
receipt.write_text(json.dumps({"status": "IN_REVIEW", "updated_utc": "2026-10-27T01:00:00Z"}), encoding="utf-8")
second = observer.run_once()
assert len(second["recent_events"]) == 1, "Timestamp rewrite must not become work progress"
receipt.write_text(json.dumps({"status": "PASS", "updated_utc": "2026-10-27T02:00:00Z"}), encoding="utf-8")
third = observer.run_once()
assert len(third["recent_events"]) == 2
assert third["recent_events"][0]["kind"] == "CONTENT_CHANGED"
assert third["recent_events"][0]["status"] == "PASS"
result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts/live_progress_v2.ps1"), "-ProjectRoot", str(ROOT), "-ActivityPath", str(observer.state_path), "-Once"], capture_output=True, timeout=20)
assert result.returncode == 0, result.stderr.decode(errors="replace")
frame = result.stdout.decode("utf-8", errors="replace")
assert "fixture_review.json" in frame and "CONTENT_CHANGED" in frame
assert "SCIENTIFIC COMPUTATION RUNNING: NO" in frame
assert "Preparation 04 [PRODUCTION_QC_PREPARATION]" in frame
(fixture / "observed_frame.txt").write_text(frame, encoding="utf-8")
report = {"status": "PASS_MONITOR_ONLY", "fixture": str(fixture.relative_to(ROOT)), "timestamp_only_rewrite_did_not_count_as_progress": True, "semantic_review_change_observed_in_next_display_frame": True, "null_pid_preparation_detail_visible": True, "no_scientific_source_modified": True}
(fixture / "test_receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
