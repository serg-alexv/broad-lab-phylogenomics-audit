# Tree 2 live progress window

The visible native PowerShell dashboard follows `state/live_stages.json` every thirty seconds (user instruction2026-10-27). It displays all fourteen registered project stages, per-stage recorded counts and elapsed times, the current worker and log tail, free host RAM/disk, and Moscow local time. It does not invent an overall percentage or a completion time.

Run on WD:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\wheel\Documents\Codex\2026-10-26\referenced-chatgpt-conversation-this-is-an\outputs\TREE2_WD_20261026\scripts\live_progress_30s.ps1" -RefreshSeconds 30
```

Use a normal or maximized window. The current required invocation uses `-RefreshSeconds 30`; the preparation collector also uses `--interval 30`. Older script defaults and historical launch receipts do not override this user instruction. `-Once` prints one noninteractive snapshot for review. Close the window or press **Q** to close only the monitor. This never stops workers. The existing `state/STOP` mechanism requests a graceful workflow stop.

A running status is displayed as verified active only when the Windows PID still exists, its exact process-creation ticks match the journal, and its command line identifies this project. Windows paths and the equivalent `/mnt/c/...` WSL project path are accepted. A reused PID, absent creation identity, missing process or unreadable command is shown as **UNVERIFIED ACTIVITY**. Stale status files and readable lock bytes do not prove activity. Terminal receipts remain the source for clean closure.

If the journal temporarily cannot be parsed, the last readable snapshot remains visible with a warning, while process liveness is rechecked. Without a usable first snapshot, stages are **NOT_REGISTERED**, not assumed running. A stale update timestamp is labelled explicitly. Later blocked/not-started stages remain visible, and missing/failed/unsearched defence states remain unknown.

## Producer contract

The workflow controller atomically publishes this JSON structure:

```json
{
  "project": "TREE2_WD_20261026",
  "updated_utc": "2026-10-26T17:30:00Z",
  "stages": [
    {
      "id": "04",
      "name": "Independent biological QC",
      "status": "RUNNING",
      "done": 10,
      "total": 1000,
      "unit": "genomes",
      "detail": "The actual substep and its limits",
      "started_utc": "2026-10-26T17:29:00Z",
      "ended_utc": null,
      "pid": 1234,
      "creation_time_utc": "2026-10-26T17:29:00.1234567Z",
      "log_path": "logs/current_worker.stdout.txt"
    }
  ]
}
```

Include stages00 through13, preserving the plan's order. `done` and `total` are actual counters; null/absent totals show no fraction. For WSL science, register the owned native Windows controller when its full command identifies the project and it separately retains the WSL child's PID, birth and exit evidence. A directly owned Windows `wsl.exe` wrapper can also be registered. Do not substitute a Linux PID. Optional source details stay in the journal or per-stage log. Log paths must stay inside the new project. The controller launches scientific stages and records terminal receipts; the dashboard is a read-only observer and does not silently retry, skip gates or start science.

New controllers atomically register `state/stages/NN.json` before starting the stage and publish presentation updates every thirty seconds or at a meaningful terminal event. Internal scientific resource/ownership polling retains its required faster cadence; an already running byte-pinned worker may keep its internal journal cadence. The publisher merges that row into its fourteen-stage journal. Preserve the current operation, actual owner identity, log and terminal receipt. A diagnostic's counters describe that diagnostic, not the whole panel. For example, completion of one QC format control leaves stage04 pending the benchmark/full QC; it must not mark the whole stage `COMPLETED`. Subsequent stage04 controllers replace the same registration before launching. Diagnostic/history receipts remain separate and immutable.

## Verification

Windows PowerShell5.1 `-Once` was exercised. An owned temporary worker verified the positive process-identity path; a one-second creation mismatch and missing creation identity were both rejected. The fixture worker was closed through its owned process handle. No real scientific worker was stopped by these checks.

The worker's host CPU/RSS numbers describe the registered Windows process. For a native controller or WSL wrapper they are not the Linux process-group peak; use the scientific worker's own resource receipt for that measurement.

Selecting text in the native console enters `Select` mode and pauses its output. Press **Esc** in that window to resume the display only; scientific workers continue independently. A selected console with a stalled frame and a healthy preparation collector is recorded as `UI_SELECTION_PAUSED`, not a worker failure. Preserve the user's selection; do not automatically clear it or restart the window. The latest diagnosed state is recorded separately in `state/monitor_30s/ui_selection_status.json`.

