# CheckM2 resource pilot: terminal evidence

At 2026-10-26 22:43:49Z, both attempted genome predictions and their native/namespace wrappers are closed. Neither produced a quality estimate. Benchmark, FASTA invariance and production QC remain held. There is no queued launcher or active scientific worker.

## Attempts

| Attempt | Result | Scientific elapsed | Sampled summed group RSS | Minimum available Linux memory |
|---|---|---:|---:|---:|
| `20261026T220700Z-2fabea30c7ba` | Unix socket path too long, before Prodigal | 62.136 s | 465,637,376 B | 2,917,232,640 B |
| `20261026T223655Z-affb024a8930` | Stopped by the explicit 2,147,483,648 B group RSS gate | 61.401 s | 3,114,455,040 B | 2,864,295,936 B |

The fresh attempt's child/group 2305 exited by SIGTERM (`-15`) and the owned group is empty. It reached the author's one-bin/two-thread gene-calling stage after model/database checks. The 600-second deadline and Linux headroom gate did not trigger. Summed RSS includes each process's resident pages; no per-PID/PSS breakdown was retained, so shared versus private physical memory is not established. Missing completeness/contamination values are null, never zero or biological absence.

The execution receipt's `started_utc` denotes controller startup before preflight. Its `elapsed_prediction_seconds` measures the separately started scientific child; the fresh run directory and live child observation establish prediction start around 22:36:55Z. Do not subtract the receipt's controller start from its end and label that duration prediction time.

## IPC correction and runtime integrity

One actual socket/Manager proof first found NTFS sockets unsupported (`errno 95`). The single private 32 MiB tmpfs fallback passed with the actual image Python 3.12, a 36-byte Manager address, and durable scientific tempfile storage after emulating the author's `--tmpdir` effect. Source proof SHA256 is `d0e08d451ef6b263089775540730b3feddef0f0e0013412e293efc3e56e59639`.

The corrected client used the kernel FD `mnt_id` to identify the effective stacked `/tmp` mount, then prewarmed only multiprocessing IPC before invoking the unchanged accepted effective bootstrap. Scientific scratch/output remained on project NTFS. The fresh attempt's IPC alias/backing and read-only image mounts closed ordinarily, loop detachment passed, and a full post-unmount hash confirmed unchanged image `c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4`. Native WSL launcher 20156 exited 1; its original process is absent and Windows/Linux ownership locks were reacquired and released.

The source checkpoint is `bacf134`, following IPC integration `90ada99`. No author binary/model/bootstrap, raw genome, base image, overlay version, WSL budget or global temporary mount was changed by the fresh attempt.

## Receipts and continuation

- Scientific receipt/failure manifest: `analysis/checkm2_pilot/runs/20261026T223655Z-affb024a8930/`. All 12 preserved manifest entries were independently rehashed after closure; no compatible protein/DIAMOND resume checkpoint exists.
- Namespace envelope: `evidence/checkm2_pilot/namespace_runs/6940a7a7e0614c938c374bc94ca171ed.json`.
- Immutable native-state snapshot: `evidence/checkm2_pilot/closed_attempts/6940a7a7e0614c938c374bc94ca171ed/manifest.json`, SHA256 `82889a0d3c573adb265e20bd4bb15582810c6a4ca482282a3eafe25c0cac899c`.
- Closure/hold: `state/checkm2_pilot_resource_failure_closure.json`, `state/checkm2_pilot_resource_hold.json`, and `state/checkm2_pilot_continuation.json`.

The new owned `STOP_CHECKM2_PILOT` has token `583d75993ca445fca988f7c7264e15e8`, SHA256 `352c2cacb99a5ba33cd8e35da845a5a32c6404eb137ae0558ac112477e69db16`. Preserve it until a separately accepted resource strategy explicitly replaces this hold. No automatic retry, extra memory, process-start override or `--genes`/`--resume` shortcut is authorized by a failed pilot. The prepared invariance adapter is unapplied because its successful baseline prerequisite is unmet.

Future cohort/final-panel work must also retain the source-only nomenclature hold crosswalk, manifest `75b64515a382f7ed4868cac7bbd0001093f79930c4e26551a68df22023bcca4a`. It does not authenticate genomes or change the 18 affected current labels/membership.
