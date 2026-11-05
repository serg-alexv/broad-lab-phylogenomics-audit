# CheckM2 private runtime image and pilot handoff

Terminal update: the fresh IPC-corrected pilot stopped on its strict summed group RSS gate before a quality score. Native20156, scientific group2305, IPC and image mounts are closed; the source image is unchanged. The new owned resource hold is authoritative. `docs/CHECKM2_RESOURCE_PILOT_OUTCOME.md` contains actual receipts; no further run follows automatically from this historical execution contract.

Current status: the sealed ext4 runtime, matching sklearn 1.6.1 overlay, forward diagnostic and mounted-client preflight passed their resource-only gates. One genome prediction then failed before Prodigal because multiprocessing's Unix socket path was too long. The scientific group, native launcher and namespace are now closed, and the source image is unchanged. `state/checkm2_pilot_baseline_failure_closure.json` binds the terminal evidence. No quality estimate or production acceptance exists. One narrow, proven IPC routing fix and one fresh bounded resource pilot are authorized; no automatic repeat is queued.

Historical setup: the first NTFS installation stopped at its one-hour deadline. The single ext4 installation completed all 133 packages; a process-local declared glibc exec-stack compatibility mode resolved the unchanged TensorFlow library's loader requirement. The base sklearn 1.9.1 warning was resolved for the diagnostic route by a complete official 1.6.1 import overlay, not by changing image/model bytes.

The old readiness waiter, native PID 18584, creation `2026-10-26T19:14:50.0603902Z`, observed its task-specific STOP and closed. Its only child was console helper 22772; both original processes are absent and the launcher's OS lock was reacquired. `state/checkm2_pilot_waiter_closure.json` records this. The specific owned hold was removed only after successful mounted-client smoke and closure; `state/checkm2_pilot_owned_hold_removal.json` records its exact token/hash. A different or user-created STOP must remain untouched.

## Runtime authority

Setup owns the image, formatting, mounting and installation. The file is `tools/checkm2_runtime_ext4.img`; the image contains `env/`, `pkgs/`, `tmp/` and `db/`. Inside the private namespace, image `env/` binds at the original canonical Linux `tools/checkm2_env` path and image DB binds at the original canonical DIAMOND path. This preserves shebangs, RPATH and CheckM2 defaults. The old NTFS partial physically remains outside these binds and is unaccepted. Windows must not inspect `prefix_windows` for program/model validation.

Final `state/checkm2_runtime_ready.json` must have `READY_FOR_RESOURCE_PILOT`, accepted import/model/RO-persistence evidence, `heavy_linux_children_closed:true`, and `requires_private_image_mount:true`. Its `runtime_image` block binds `path`, `sha256`, `bytes`, `filesystem_uuid`, `seal_receipt_path` and `seal_receipt_sha256`. Only the seal written after final installation, ordinary clean unmount, loop detachment and source-image hashing is authoritative. A whole-image hash is never claimed while mounted RW.

The native launcher additionally verifies the environment receipt hash, COMPLETE status, unchanged host registry, passed RO persistence and closed smoke children. It requires the installer's exact Windows process creation identity to have exited and its actual byte lock to be released. A readable lock file or missing PID alone is insufficient.

## Execution route

`scripts/launch_checkm2_pilot.ps1` writes an immutable token-specific request and the actual native WSL PID/creation receipt. It invokes the existing `checkm2_private_setup_ns.sh outer run` wrapper with the project-owned `checkm2_pilot_image.sh`. That shell sets project-local temp/cache controls and calls `checkm2_pilot_image_entry.py`. The entry delegates mount ownership exclusively to setup's `checkm2_runtime_image.py`:

```text
python3 -B checkm2_runtime_image.py --receipt <token_mount.json>
  --effective-runtime <validated_manifest> --effective-runtime-sha256 <sha256>
  --readonly-exec python3 -B checkm2_ipc_alias.py --receipt <token_ipc.json>
  --proof <capability_proof.json> --proof-sha256 <sha256> --token <token>
  --exec python3 -B checkm2_pilot.py <operation> ...
```

`--receipt` precedes `--readonly-exec`, whose remaining arguments are the child command. The helper exports `TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED=1` and `TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT` only inside the mounted namespace.

Before any program/model hashing, the pilot checks current namespace identity, final seal/SHA/UUID binding, actual image/prefix/DB read-only flags, single-link backing identity, live loop backing inode/offset/size and RO/AUTOCLEAR flags, actual ext4 UUID, mount source and `ro,nodev,nosuid` flags, journal suppression (`noload`/`norecovery`), executable access, and exact `/env` and `/db/uniref100.KO.1.dmnd` bind roots. It performs no mount or device mutation. Marker booleans alone cannot admit a runtime.

Inside the namespace it then verifies program 1.1.0, DIAMOND 2.1.11, the installed/models manifests, all nine official asset hashes and the explicit extracted database hash. Missing author-table entries are preserved as limitations; model-load success is engineering readiness, not biological calibration. Matching-version execution additionally requires `state/checkm2_forward_ready.json`, the validated effective-runtime manifest, all 894 overlay files bound read-only, and the unchanged audited preload bootstrap. The four exact effective environment keys are GLIBC_TUNABLES, PYTHONPATH, PYTHONNOUSERSITE and PYTHONDONTWRITEBYTECODE. Plain PYTHONPATH is insufficient because author main prepends the base site-packages. The new IPC plumbing must remain separate from the accepted bootstrap bytes and must be bound into the pilot options/namespace proof.

## Mount smoke before prediction

After final READY and actual installer closure:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/launch_checkm2_pilot.ps1 -MountSmoke
```

This performs namespace/tool/hash preflight without predicting a genome. It intentionally permits the owned prediction hold to remain, while respecting global STOP. Require the token's envelope in `evidence/checkm2_pilot/namespace_runs/` to have `NAMESPACE_CLOSED_AND_VERIFIED`, operation `MOUNT_SMOKE_ONLY`, helper exit 0, an unchanged final image SHA, and a successful prediction-free preflight receipt. The helper unbinds DB/env, ordinarily unmounts ext4, closes descriptors and proves AUTOCLEAR, then removes the raw-image RO file bind. No lazy unmount establishes readiness.

Only after this gate passes may the controller remove the specific owned prediction hold, verifying its token against the old closure receipt. A user-created or different STOP flag is preserved. Then the same launcher without `-MountSmoke` runs one authorized resource pilot. Do not queue another launcher or installer while a native WSL worker or unproven prior namespace remains.

## Bounds and completion

Prediction retains two CPUs/threads, author lowmem block 0.5, a 600-second scientific deadline, 2 GiB measured process-group RSS and at least 1 GiB Linux headroom. Source-image verification is separately bounded at 600 seconds and publishes progress; post-unmount verification checks STOP/headroom. Native outer waiting is bounded at 3600 seconds. An outer timeout records the remaining WSL identity and unproven closure, blocks relaunch and does not claim to have killed a child.

The inner scientific result remains pending namespace closure. The outer envelope verifies ordinary mount closure and rehashes the unmounted source image before the live stage becomes COMPLETED. A numeric core without its successful namespace receipt is held and preserved, not recomputed. Fresh namespace/loop identities are execution evidence; they do not invalidate an otherwise exact scientific input/tool/model/database/options resume binding. A changed runtime image does invalidate it.

The IPC routing gate additionally verifies the current `/tmp` alias namespace, exact backing inode, `rw,nodev,nosuid,noexec` protections and the proven backend. An O_PATH directory FD's kernel `mnt_id` selects the actual effective mount when the older private RO `/tmp` bind is also present; mount list order is not authority. A tmpfs fallback is fixed at 32 MiB. The stable proof/helper/IPC-bootstrap source hashes form part of the scientific execution binding; each launch's namespace/inode receipt does not. Target Python starts with short temp environment, then the IPC shim caches only multiprocessing's directory before invoking the unchanged accepted bootstrap. Author `--tmpdir` still directs ordinary scientific scratch to durable run storage. Both IPC alias/backing and image mounts must close ordinarily before the final envelope can pass.

No failure, missing score, stopped operation or unsearched defence state becomes biological absence. One resource pilot never freezes the panel or admits all genomes. Compatibility-warning review and author control runs remain separate gates before full-panel QC.

## Verification and continuation

Fixture evidence covers 16 controller/schema checks, 20 namespace/loop/IPC-binding checks, 6 final-hash stop/headroom/deadline checks, 7 native PowerShell checks and 5 effective-runtime gate checks. Simulated RO observations are explicitly fixture-only. These tests mount nothing and predict nothing. Actual successful mounted-client smoke is token `9233637809ba43af836823d28f487d77`, closed at 22:00:01Z with unchanged source image. A subsequent genome pilot failed on its IPC socket path; fixture success is not represented as scientific success.

`state/checkm2_pilot_continuation.json` is the explicit continuation handoff for the active Tree2 heartbeat. No unregistered auto launcher is left running. Read fresh READY, creation identities, OS locks and actual receipts before advancing. Preserve all raw sources, accepted ANI/curation outputs and the prepared ten-genome template. No GitHub or uploads.
