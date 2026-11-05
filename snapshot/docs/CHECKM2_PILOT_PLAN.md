# One-genome CheckM2 resource pilot

Terminal update: the authorized fresh IPC-corrected attempt also stopped before a score, on the explicit summed group RSS gate. Both native/scientific/IPC/image closures are proven; further prediction is held. See `docs/CHECKM2_RESOURCE_PILOT_OUTCOME.md` for measured evidence and continuation limits. The following plan/history does not authorize another run.

The first guarded genome prediction ran on 2026-10-26 and failed before Prodigal: Python's multiprocessing Manager could not create its Unix socket under the long project temp path (`AF_UNIX path too long`). The scientific group closed after 62.136 seconds, with sampled peak RSS 465,637,376 bytes and minimum available Linux memory 2,917,232,640 bytes. No completeness or contamination estimate exists. The source image was unchanged after ordinary namespace closure; native launcher 23504 exited 1 at 22:12:45Z. Evidence is preserved in `analysis/checkm2_pilot/runs/20261026T220700Z-2fabea30c7ba/` and `state/checkm2_pilot_baseline_failure_closure.json`.

One narrow IPC plumbing fix and one fresh bounded diagnostic pilot are authorized after an actual short-path socket/Manager proof. The original failure remains immutable. Scientific scratch stays on project NTFS; a short private alias is for multiprocessing IPC only. The original NTFS runtime remains unaccepted. Runtime execution requires the sealed private ext4 image and the gates in `docs/CHECKM2_RUNTIME_IMAGE_CONTRACT.md`.

`scripts/checkm2_pilot.py` defaults to preparation only. The planned input is **GCF_013267415.1, Abiotrophia defectiva**, a current source-supported, metadata-QC-passing genome. The genomic FASTA is bound to its acquisition SHA256. Source NCBI CheckM v1.2.4 estimates of 95.33% completeness and 1.1% contamination provide context; they are not truth or calibration.

## Admission and limits

Prediction requires `state/checkm2_runtime_ready.json` with `READY_FOR_RESOURCE_PILOT`, affirmative import/model smoke flags, CheckM2 1.1.0, DIAMOND 2.1.11 and closed installer children. The environment receipt must be COMPLETE, hash-bound and confirm the outside registry was unchanged. Installed and models manifests must match the READY hashes. All nine actual author model/scaler/reference assets must match the model-loading smoke record. Four assets are absent from the upstream version-hash table; they must instead match the independently inspected official package payload. Missing entries are documented limitations, not invented author-table passes.

Database version 3 requires its own extracted binary size/SHA256 receipt. An archive hash cannot substitute for that hash. The explicit database path is `tools/databases/checkm2_v3/data/CheckM2_database/uniref100.KO.1.dmnd`. No global database setter is used.

There must be no other heavy scientific/install/model-smoke worker. Use two threads and at most two permitted CPUs; author `--lowmem` keeps the unmodified DIAMOND block size at 0.5. Stop at 600 seconds, group RSS above 2 GiB, Linux available memory below 1 GiB, less than 40 GiB volume reserve, or a project STOP flag. There is no virtual-address cap: mapped address space differs from RSS. Failure does not authorize more memory, a global WSL change or an author-code patch.

## Isolation and ownership

`scripts/launch_checkm2_pilot.ps1` records the actual Windows WSL-launcher PID, creation time and unique token. The Linux controller requires the matching receipt and records native creation ticks/process group. Windows and Linux OS locks prevent duplicates. The optional readiness waiter starts no prediction until its gate passes.

Raw input is copied and rehashed inside a unique run directory. Scientific temp, Keras, XDG, Matplotlib and Numba locations remain inside the project; HOME stays unchanged. Stock CheckM2's `--tmpdir` also changes Python's global tempfile directory. Therefore the planned fix must prewarm only multiprocessing's own short IPC directory before unchanged author code, while preserving the long durable scientific temp directory. The backend proof must test a Manager after emulating that author temp change. No `--force` or `--remove_intermediates` is used. The live publisher consumes `state/checkm2_pilot_progress.json` through stage 04. The controller records substep, native launcher identity, Linux resources and log path continuously.

`PYTHONWARNINGS=default` and complete stdout/stderr preserve emitted compatibility warnings. Stock CheckM2 sets TensorFlow C++ logging to level 3 and its Python logger to FATAL; this behavior is recorded without patching it. The accepted resource-only route uses the complete official sklearn 1.6.1 overlay and unchanged audited bootstrap, matching the scaler's serialized version. Its six-row synthetic scaler/NN/selection controls passed with no version warnings; those controls and successful loading do not establish biological calibration or production acceptance. One numeric result would not establish it either.

## Results and recovery

Each `analysis/checkm2_pilot/runs/<timestamp-binding>/` preserves input/tool/model/database/options binding, executed controller source, command/environment, author outputs, resource/process/closure receipt, intermediate inventory and result or failure receipt. A successful report has exactly the expected accession and finite Completeness/Contamination. Completeness must be 0–100; contamination must be nonnegative. High estimates are not coerced to zero. The 95/5 screening flag is descriptive; one pilot never freezes the panel or grants production acceptance.

Partial Prodigal and DIAMOND outputs are preserved. Author `--resume` requires an exact binding, valid nonempty proteins, both DIAMOND completion/postprocessing sentinels, nonempty valid 12-column rows referring to preserved proteins, and unchanged intermediate hashes. Mere file presence is insufficient. Exact successful results are verified and reused without recomputation. Prior failures remain held; resource failure is not automatically retried. Missing/failed values remain null and have no biological absence interpretation.

Sixteen controller fixture checks are in `evidence/checkm2_pilot/controller_selftest.json`. They cover malformed/nonfinite/mismatched quality rows, unaccepted models/version, path isolation, namespace admission and partial/empty intermediates. Additional image/entry/native fixtures are documented in the runtime contract. These checks run no model or genome prediction.

## Ten-genome follow-on, prepared only

`scripts/prepare_checkm2_benchmark.py` prepares an immutable input/options template; it cannot launch prediction. Its scope is **919 source-supported current-panel candidates** (824 metadata pass; 95 pending) plus **23 source-supported ancillary metadata-QC-review isolates**. Only the metadata quality hold is investigable in that ancillary queue. Source/taxonomy holds, unknown provenance, MAGs and SAGs remain held/excluded regardless of a later QC score.

The provisional benchmark contains ten genera across five families: seven current-panel metadata-pass genomes, two ancillary low-completeness controls and one ancillary high-contamination control. It excludes the first pilot accession to avoid repetition. Every FASTA and acquisition/source binding is verified; selection grants no quality/taxonomy acceptance. The template retains two CPUs/threads, author lowmem 0.5, 2 GiB group RSS, 1 GiB Linux headroom, a 600-second bound and intermediate preservation.

The follow-on requires the one-genome model/resource/schema gate and compatibility review first, then a concrete controller with native ownership, locks, live stage registration, exactly ten valid rows and atomic receipts. The prepared template is not an executable or running scientific stage. Full-panel mini-batches remain a later gate.
