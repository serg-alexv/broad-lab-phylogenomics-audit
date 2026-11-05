"""Synthetic source/UI policy fixtures. Does not run a monitor or scientific probe."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import subprocess
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("monitor_v3_source", ROOT / "scripts/prep_activity_collector_v3.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture = ROOT / "work" / ("monitor_v3_source_fixture_" + uuid.uuid4().hex)
fixture.mkdir(parents=True)
source = fixture / module.SOURCE_CHECKPOINT
source.parent.mkdir(parents=True)
manifest_rel = "metadata/fixture_source_manifest.json"
manifest_path = fixture / manifest_rel
manifest_path.parent.mkdir(parents=True)
manifest_path.write_text('{"fixture_sources":111}', encoding="utf-8")
manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
source.write_text(json.dumps({"status": "N1_HELD_SOURCE_CHECKPOINT_NO_SCIENTIFIC_GRANT", "source_manifest": {"path": manifest_rel, "sha256": manifest_sha}}), encoding="utf-8")
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
admission_rel = "checkpoints/N1_ADMITTED_FIXTURE_LATER/receipt.json"
admission = fixture / admission_rel
admission.parent.mkdir(parents=True)
admission.write_text('{"status":"N1_ADMISSION_CHECKPOINT_NOT_EXECUTION_RESULT","fixture_files":10}', encoding="utf-8")
artifacts = {
    module.SOURCE_CHECKPOINT: {"sha256": source_sha, "mtime_utc": "2026-10-27T08:40:47Z"},
    manifest_rel: {"sha256": manifest_sha},
    admission_rel: {"sha256": hashlib.sha256(admission.read_bytes()).hexdigest(), "mtime_utc": "2026-10-27T08:53:43Z"},
}
selected = module.checkpoint_binding(fixture, artifacts, source_sha)
assert selected["source_checkpoint"] == module.SOURCE_CHECKPOINT
assert selected["manifest_matches"] is True
assert selected["source_checkpoint_exact"] is True
assert selected["admission_checkpoint"]["path"] == admission_rel
# Admission cannot rescue a missing/mismatched source freeze.
bad = {**artifacts, manifest_rel: {"sha256": "0" * 64}}
assert module.checkpoint_binding(fixture, bad, source_sha)["manifest_matches"] is False
assert module.checkpoint_binding(fixture, artifacts, "0" * 64)["manifest_matches"] is False
missing = dict(artifacts)
missing.pop(module.SOURCE_CHECKPOINT)
assert module.checkpoint_binding(fixture, missing, source_sha)["manifest_matches"] is False
# The observer preserves the previous complete snapshot on a bounded Windows
# access-denial interval, and a later publication can recover normally.
atomic_path = fixture / "optional_snapshot.json"
module.atomic_json(atomic_path, {"status": "OLD_VALID"})
original_replace = module.os.replace
denials = 0
def denied_once(source_path, target_path):
    global denials
    denials += 1
    if denials == 1:
        raise PermissionError("synthetic sharing interval")
    return original_replace(source_path, target_path)
with patch.object(module.os, "replace", side_effect=denied_once), patch.object(module.time, "sleep"):
    module.atomic_json(atomic_path, {"status": "RECOVERED"})
assert denials == 2 and json.loads(atomic_path.read_text())["status"] == "RECOVERED"
with patch.object(module.os, "replace", side_effect=PermissionError("synthetic bounded denial")) as blocked, patch.object(module.time, "sleep"):
    try:
        module.atomic_json(atomic_path, {"status": "UNCOMMITTED"})
        raise AssertionError("Bounded denial should remain explicit")
    except PermissionError:
        pass
    assert blocked.call_count == 30
assert json.loads(atomic_path.read_text())["status"] == "RECOVERED"
for filename in ("prep_activity_collector_v3.py", "test_monitor_v3_source_only.py"):
    ast.parse((ROOT / "scripts" / filename).read_text(encoding="utf-8"))

# Extract only one pure PowerShell policy function. No Get-Frame, Get-Process,
# runtime probe, console creation, or collector execution occurs in this fixture.
ps_source = ROOT / "scripts/live_progress_v3.ps1"
ps_fixture = fixture / "policy_fixture.ps1"
quoted = str(ps_source).replace("'", "''")
ps_fixture.write_text("""$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile('""" + quoted + """',[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'V3 PowerShell source has parse errors'}
$function=$tree.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-PreparationGatePolicyV3'},$true)
if(-not $function){throw 'Pure gate-policy function missing'}
. ([scriptblock]::Create($function.Extent.Text))
$active=Get-PreparationGatePolicyV3 1
$idle=Get-PreparationGatePolicyV3 0
$terminal=Get-PreparationGatePolicyV3 0 'PENDING_NATIVE_EXIT_AND_COMPARISON'
if($active.ShowLaunchChecklist -or $active.Notice -match 'unknown until'){throw 'Active worker retained obsolete launch ETA'}
if($terminal.ShowLaunchChecklist -or $terminal.Notice -match 'unknown until'){throw 'Post-launch review retained obsolete launch ETA'}
if(-not $idle.ShowLaunchChecklist -or $idle.Notice -notmatch 'unknown until'){throw 'No-worker preparation gate policy changed unexpectedly'}
$raw=[IO.File]::ReadAllText('""" + quoted + """')
if($raw -notmatch '\\$GatePolicy=Get-PreparationGatePolicyV3 \\$VerifiedActive.Count'){throw 'Policy not connected to verified activity count'}
if($raw -notmatch 'if\\(\\$GatePolicy.ShowLaunchChecklist\\)'){throw 'Launch checklist not gated by policy'}
'PASS_PURE_UI_POLICY_ONLY'
""", encoding="utf-8")
result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_fixture)], capture_output=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
assert result.returncode == 0, result.stderr.decode(errors="replace")
assert b"PASS_PURE_UI_POLICY_ONLY" in result.stdout
protected = {"scripts/live_progress_v2.ps1": "b239e461166346d9eb03ed390609ac1d9ccd365231b1f30aa4fb28662e66f39f", "scripts/prep_activity_collector_v2.py": "0188a9bb0005a2cdaa7d38e8e18ea36c5e0966f305adf4018233529aeb5b479e", "scripts/live_stage_publisher.py": "0dd272f46a519956e769163760a8812c7be60320ab2734de050d9cf8bebee8fe"}
for rel, expected in protected.items():
    assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected, rel + " changed"
report = {"status": "PASS_SOURCE_ONLY_NOT_APPLIED", "source_checkpoint_explicit_despite_newer_admission": True, "admission_checkpoint_separately_reported": True, "bad_or_missing_source_binding_remains_false": True, "active_verified_worker_hides_launch_checklist_and_ETA": True, "post_launch_review_hides_obsolete_ETA": True, "no_worker_retains_preparation_checklist": True, "transient_access_denial_recovers": True, "persistent_access_denial_bounded_30_and_prior_snapshot_preserved": True, "v2_and_old_publisher_bytes_preserved": True, "monitor_or_collector_launched": False, "scientific_or_runtime_probes": False, "fixture": str(fixture.relative_to(ROOT))}
(fixture / "test_receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
