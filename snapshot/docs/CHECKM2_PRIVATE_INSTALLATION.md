# CheckM2 private offline installation

Installation began 2026-10-26 at 18:47:30 UTC under native controller PID6056,
with its recorded creation identity. This is a tool-setup stage, not a genome
quality result.

## Accepted inputs and filesystem boundary

The pinned CPU-only closure contains133 packages,727,128,168 compressed bytes,
and3,793,959,609 regular unpacked bytes. Its manifest SHA256 is
`a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52`.
The installer waits for the final cache+inspection receipt, independently checks
every archive's size/SHA256 again, checks the preserved original notice manifest,
and requires the native cache lock to be free before taking progress ownership.

Three ncurses terminfo case-only filename pairs were found before installation.
The new empty project prefix `tools/checkm2_env` and extraction cache
`tools/checkm2_runtime_pkgs` were given directory-local case-sensitive flags.
Nested upper/lowercase test files remained distinct; their contents were moved
intact to project evidence. No global case setting was changed. See
`evidence/checkm2_runtime/case_sensitive_directory_proof.json`.

The existing conda executable is read only inside the verified private namespace.
The actual operation is an offline explicit install; it does not solve again or
access network endpoints. All package, temporary and XDG caches are project-owned.
The private `/root/.conda` bind protects the host registry; `HOME` stays unchanged.
The native controller captures the real host registry hash, nanosecond timestamp
and size immediately before and after the operation. Any mismatch prevents
readiness and is never automatically overwritten.

## Readiness gates

The four-phase controller performs:

1. Safe extraction of the already verified CheckM2v3 database, retaining its
   original archive and a separate extracted file SHA256 receipt.
2. Exact133-package CPU installation at the case-sensitive prefix. A pre-existing
   complete matching prefix can be reused; an unknown/incomplete prefix is
   preserved and stops automatic installation rather than being removed.
3. CLI/import/model-loading smokes: CheckM2, DIAMOND, Prodigal and pinned scientific
   library versions; all bundled data/model hashes checked against the author's
   table; both LightGBM models, Keras model and scaler loaded; author test-genome
   checksums and database compatibility checked. No genome prediction is run.
4. Full installed-file and model manifests, closed child-process groups, followed
   by the native outside-registry audit and atomic readiness publication.

All child groups inherit two-CPU affinity. Runtime/model smokes are bounded by
sampled group RSS2GiB, at least1GiB Linux available memory, two compute threads,
40GiB backing-volume reserve and ten-minute smoke deadlines. Installation has a
one-hour command deadline. STOP is checked while extraction and child monitoring
progress. Partial outputs and terminal receipts remain available on failure.
Warnings are recorded; source/program models are not patched.

Only `state/checkm2_runtime_ready.json` with status
`READY_FOR_RESOURCE_PILOT`, together with a matching complete
`evidence/checkm2_runtime/tool_environment_receipt.json`, authorizes the separate
scientific resource pilot. Environment installation, model loading and genome
quality acceptance are distinct states. No genome is admitted merely because
the runtime loaded successfully.

## Files

- `scripts/checkm2_private_install_controller.py`: native lock, cache handoff,
  archive identity, before/after registry audit and readiness commit.
- `scripts/checkm2_private_install.sh`: private process-local runtime settings.
- `scripts/checkm2_private_install_linux.py`: extraction, exact install,
  process-group budget/closure and installed manifests.
- `scripts/checkm2_runtime_smoke.py`: supported CLI and model-loading checks.
- `evidence/checkm2_runtime/tool_environment_receipt.json`: eventual terminal
  result; absence means not ready.
- `state/tool_setup_progress.json`: live phase and real process identity.

The source checkpoint and live journal do not claim installation success before
the terminal gates pass. Logs and original notices remain local; GitHub and
uploads remain prohibited.

## First attempt outcome: bounded timeout, not ready

The primary Conda process began at 18:49:16 UTC and reached its fixed one-hour
deadline while files were still being materialized on the Windows filesystem.
Termination grace and group closure finished at 19:49:27 UTC; the native
controller exited after its final registry audit at 19:49:28 UTC. The sampled
process-group peak was 1,901,805,568 bytes, below the 2 GiB ceiling. This is an
installation failure, with no scientific prediction, CLI smoke, model-loading
pass, or readiness flag.

All 133 original archives were independently rehashed after termination and
still match the pinned official SHA256 values (727,128,168 compressed bytes).
All 133 cache extraction records and the incomplete project-owned prefix remain.
No retry, overwrite, prefix removal, or new dependency resolution was launched.

`install_exit.json` records exit -9 and an empty process group. Independent closure
proof confirms that native PID6056 and Linux namespace main PID1412 are absent,
Linux group1436 is empty, and the native installation lock is released. The
shared host registry's bytes, SHA256, size, timestamp, and absence of the private
canary are identical before and after the attempt.

Receipts are in `evidence/checkm2_runtime/`: `tool_environment_receipt.json`,
`installation_closure_proof.json`, and `cache_post_install_timeout_audit.json`.
Read-only probes document genuine progress through extraction, 511 prefix
rewrites, and subsequent file creation; they do not accept the partial prefix.
Recovery must use these closed-process and immutable-cache receipts and must
not treat the incomplete directory as an installed environment.
## Upstream asset-table discrepancy found before the first smoke

Independent review of the unchanged official CheckM2 1.1.0 package found that four
current model/data assets have hashes absent from its bundled
`version_hashes_1.1.0.json`. The affected assets are `specific_model_COMP.keras`,
`scaler.sav`, `min_ref_rsdata_v1.npz`, and `cosine_table.pkl`. This is recorded in
`evidence/checkm2_runtime/author_table_audit.json`; it is not reported as a passing
author-table check. The package's original `info/paths.json` pins all nine assets.

Before the separate smoke helper had executed, its added all-assets-in-author-table
assertion was corrected to require each installed asset's SHA256 and size to match
that original package metadata, whose preserved bytes and official archive SHA256
are checked independently. Author-table matches and missing hashes are reported
per asset. The original helper, its hash, execution timing, and correction receipt
are preserved in `evidence/checkm2_runtime/history/smoke_author_table_correction/`.
The running installation driver, scientific package, models, and strict author
database compatibility check were not changed. Model loading and the later
scientific resource pilot remain required.
