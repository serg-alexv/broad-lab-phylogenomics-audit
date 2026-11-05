# Monitor V3 source-only correction — held, not activated

The running V2 GUI, collector and original stage publisher stay unchanged. No V3 monitor or collector has been launched. These new sources are prepared only for a separately reviewed replacement after the active scientific worker has terminal closure evidence.

Two V2 display findings are reproduced by source inspection. First, V2 chooses the newest receipt from all `checkpoints/N1*/receipt.json`; the later10-file `N1_ADMITTED` receipt has no `source_manifest` binding and therefore makes the displayed bound flag false despite the valid earlier114-file source checkpoint. Second, V2 prints its launch checklist and unknown-launch ETA unconditionally, even while it displays a freshly verified active scientific worker.

`scripts/prep_activity_collector_v3.py` explicitly binds `checkpoints/N1_SOURCE_HELD_20261027T084045Z/receipt.json`, requiring its pinned SHA256 `081b7e96114c97f48ccb8e7192d1f98d70806b2ef5b99c2bd30ab4e7aba6e229`, the source-checkpoint status, and the manifest hash binding. A newer `N1_ADMITTED` receipt is reported separately as admission evidence; it cannot substitute for the source freeze or establish an execution result. Missing/mismatched source evidence still produces a false bound flag.

`scripts/live_progress_v3.ps1` shows the explicit source-freeze receipt and the separate admission checkpoint. Its preparation gate policy receives the existing freshly verified active-worker count. With a verified active worker it hides the launch checklist and obsolete launch ETA, and directs attention to the worker operation/log/terminal receipts. Without a verified worker it retains the preparation checklist. It does not infer scientific success or acceptance from launch.

V3 sources use a new `state/monitor_v3/` sidecar namespace and V3 schema/title if activated later. Current V2 bytes and launch receipts remain preserved. No launcher for V3 is supplied by this change, and no global setting, scientific source pin, lease, runtime or N1 state is modified.

`scripts/test_monitor_v3_source_only.py` passed synthetic fixtures for a newer admission checkpoint, separate admission reporting, missing/wrong source bindings, and active/idle UI policy. It imports only the observer source and invokes only one extracted pure PowerShell policy function, with no process query, monitor/collector launch or scientific/runtime probe. The test also verifies the unchanged V2 display/collector and original publisher hashes. Fixture evidence is retained at `work/monitor_v3_source_fixture_6ddd424d12694bdea0a55a4a260d2674/test_receipt.json`.

The correction is specific to this accepted N1 source freeze. Any future source tuple requires an explicit new reviewed binding. Deployment and interactive V3 verification remain not run.
