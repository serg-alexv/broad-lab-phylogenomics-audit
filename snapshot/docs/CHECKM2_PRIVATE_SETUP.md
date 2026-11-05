# Private CheckM2 installation preparation

The `WAITING_TOOL_SETUP` gate is an internal engineering step, not a request for
user approval. The CheckM2 database is already verified. Its compatible runtime
and a measured scientific pilot are separate gates.

## Verified private installation boundary

On 2026-10-26 at 17:50:54 UTC, a bounded namespace proof passed. The new worker
used private Linux mount and network namespaces; these mounts disappear with
that worker and do not change host mounts, networking configuration or WSL
resource settings.

- The effective mounts at `/`, `/mnt/c`, `/tmp`, `/var/tmp` and `/run` are read only
  inside the private worker.
- The Tree2 project is a writable bind mount at its existing exact path.
- `/root/.conda` inside the worker maps to
  `work/checkm2_private_registry/` in this project. Its canary appeared only there.
- `HOME` remained `/root`. No HOME redirection was used.
- Package, environment, temporary and XDG cache paths are explicitly project-owned.
- The host `/root/.conda/environments.txt` SHA256, mtime in nanoseconds and size
  were identical before and after the proof. No host canary was created.

This proves the stated mapping, not that the CheckM2 environment is installed,
nor that every possible filesystem path is inaccessible. `/proc` and device
mounts retain their normal process-facing roles. Only trusted, inspected setup
scripts under this project may be run by this wrapper. Installation and all
post-link behavior still require their own result and outside-registry audit.

Evidence: `evidence/checkm2_runtime/namespace_proof_receipt.json` and
`namespace_mapping.json`. The first probe's validator misread stacked findmnt
entries; it failed without host registry changes and is preserved under
`evidence/checkm2_runtime/history/first_namespace_probe/`. The corrected proof
uses kernel `statvfs` effective read-only flags.

## Protocol

`scripts/checkm2_private_setup_ns.sh outer proof` runs only the mapping proof.
`scripts/checkm2_private_setup_ns.sh outer run <absolute-project-script>` runs a
trusted project script after the mapping checks. `TREE2_PRIVATE_NAMESPACE_VERIFIED=1`
is set only inside the wrapper. The selected runtime must be resolved offline
from the saved official conda-forge/Bioconda metadata; package URLs and hashes
must be recorded before any actual package transfer or linking.

The dependency resolver owns the next bounded dry-run and writes
`evidence/checkm2_runtime/solve.json`. Its actual worker identity and progress
must be registered in `state/launch_tool_setup.json` and
`state/tool_setup_progress.json`. A completed proof does not mean the environment
or genome QC has completed. No scientific prediction runs at this preparation
stage.

The first offline dependency-resolution attempt ran inside the verified private namespace. It exited with cached file-channel metadata unavailable in a cold conda offline cache, not a missing verified CheckM2 package or an isolation failure. Host registry SHA256, nanosecond mtime and size remained identical; measured maximum RSS was126,684KiB. A bounded configuration correction permits reading the same local file:// channel metadata while the private network namespace stays disconnected. No package/version constraint or source quality gate is relaxed.
