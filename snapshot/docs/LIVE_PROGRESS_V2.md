# Visible preparation and scientific progress

The new native window is **TREE 2 - WD - LIVE PROGRESS V2**. It refreshes every four seconds. The preparation mode, scientific-worker answer, full current preparation detail, latest substantive source/review/checkpoint change with Moscow time and age, and the launch checklist appear before the all-stage table. In a small window the view stays at the action panel; the complete frame and all stages also remain in `state/monitor_v2/display_last_frame.txt`.

Closing the window or pressing Q closes only this display. It does not stop scientific workers. The independent stage publisher remains unchanged. Workflow stop requests still use `state/STOP` under the existing controller contract.

## What is evidence

`scripts/prep_activity_collector_v2.py` is a lightweight native Python observer. It reads project-local N1 source/metadata/review/checkpoint receipts, selected script and document timestamps, and local Git commit metadata. It imports no scientific code, starts no scientific work, invokes no WSL or model/runtime probe, issues no admission, and writes only its new sidecars under `state/monitor_v2/`.

The observer compares content hashes. JSON clock/heartbeat fields are excluded from its semantic fingerprint; changing `updated_utc` alone creates no progress event and does not advance the meaningful-change clock. Baseline artifact times are explicitly labelled as saved evidence. Local source commits can be preparation evidence; they are not evidence of a running computation. Monitor/observer timestamps and CPU activity are never counted as scientific progress.

The display reads the existing `state/live_stages.json` and the new `state/monitor_v2/preparation_activity.json`. Active scientific workers require a freshly matching Windows PID, exact creation time and project command path, including the equivalent `/mnt/c/...` WSL path. A missing or reused PID produces an unverified state. Host CPU/RSS for a WSL launcher remains labelled as host data, not Linux process-group memory.

`state/preparation_gates_v2.json` is the controller-owned gate summary. Its mode, detail and gate list update the display automatically; the observer never changes it. The named component PASS statuses do not grant final-panel or taxonomy acceptance. Missing admissions remain unissued. There is no invented percent, ETA or promise of a successful launch. Unknown/failed/unsearched defence calls remain unknown.

A stale observer (>20 seconds) is distinguished from a refreshing display. No substantive observed source/review/checkpoint change for ten minutes produces an activity warning; that warning does not infer that a reviewer stopped working. Once a registered scientific worker starts, its verified PID, current operation and log are shown from the existing stage journal.

## New files and launch evidence

- `scripts/live_progress_v2.ps1`: the visible WinPS5.1-compatible display; `-Once` prints one fresh frame.
- `scripts/prep_activity_collector_v2.py`: the preparation observer; continuous operation defaults to four seconds.
- `scripts/launch_live_progress_v2.ps1`: one-time identity-bound replacement of the original GUI. It first verifies the new visible title/handle, process creation identity and two fresh frames. It never stops/restarts the existing stage publisher or a scientific worker. `-KeepOldConsole` stages the new display and preserves the old GUI for separate verified closure. This historical upgrade launcher deliberately names the original GUI identity; it is not a generic future restart tool.
- `scripts/test_monitor_v2.py`: bounded non-scientific fixtures, retained under `state/monitor_v2/fixture_*`.
- `state/monitor_v2/launch_console.json` and `launch_collector.json`: exact command, PID, UTC creation time, Windows FILETIME, script and SHA256.
- `state/monitor_v2/display_health.json`, `display_last_frame.txt`, `preparation_activity.json`, and `events.jsonl`: current display/observer evidence.
- `state/monitor_v2/old_console_closure.json`: birth-checked original display closure after new-window verification.
- `evidence/monitor/v2_upgrade_20261027T084754Z/`: immutable launch and observed-frame evidence for this replacement.

## Verified replacement on 2026-10-27

New GUI PID20544 was born at08:47:55.9789108Z; collector PID9560 at08:47:55.6147461Z. The new GUI proved a visible native handle464455356 and exact V2 title, with frame2 at08:48:01.6285617Z before any old-GUI closure. After fresh birth and command checks, only old GUI PID13584/birth2026-10-26T17:34:43.0259267Z was closed, with observed native exit-1 at08:48:52Z. Exit-1 belongs to terminating the superseded monitor, not a scientific outcome. Publisher PID5812/birth00:50:40.4735797Z and its bytes were preserved. All111 frozen source rows were rehashed exact after replacement.

WinPS5.1 one-frame rendering passed. A bounded synthetic review receipt changed from IN_REVIEW to PASS and appeared in the next display frame. A timestamp-only JSON rewrite created no event. The pid-null preparation detail remained visible and the real preparation-only frame reported scientific computation NO. These tests changed only dedicated monitor fixture/sidecar files; they did not touch scientific sources or outputs.
