# Live execution and continuation

The initial batch is a bounded 1,000-genome PROVISIONAL acquisition input, not a frozen scientific panel. Current accession census and all per-page receipts are local. The original snapshots and validated outputs are preserved.

At 2026-10-26T16:22Z the main acquisition process PID20924 was live with a matching creation identity. The finalizer and queued-acquisition processes wait on that exact owned process; stale PIDs are insufficient for a restart. Fresh state/launch_*.json, matching exit receipts and OS locks take precedence over these historical IDs.

After that batch exits COMPLETE or PARTIAL_FAILURE, the queued workflow acquires35 additions and23 QC_REVIEW_ONLY genomes. The review-only genomes remain outside production acceptance and retain all original failed95/5 metadata reasons. A separate bounded replacement queue is being prepared for source-sequence rejections. All committed data are retained. No automatic biological-QC, tree or defence stage bypasses its gates.

Each accession commit contains its source package SHA256, per-file hashes, exact metadata and acquisition/QC receipt. Checkpoints archive mutable selection/state and retain immutable manifest snapshots. Local Git uses SHA256 objects and has no remote. No GitHub or cloud publication is configured.

To request a graceful stop create state/STOP; workers check this during metadata requests/streaming. Allow their request timeouts to expire, then verify matching terminal receipts and lock release. Preserve partials. Removing STOP is an intentional resume action; rerun the same immutable acquisition input after fresh process/lock reconciliation. Do not start a second controller just because an old PID is absent.

The ten-genome exploratory marker pilot completed after one bounded MMseqs indexing correction. It reused the ten accepted annotation hashes and the identical combined input, and did not reuse any older marker panel. See analysis/pilot10/mmseqs_failure_and_correction.json. Production marker validation is not complete.

Independent acquisition validation has its own snapshot denominator in qc/acquisition_validation.json. It is not completeness/contamination validation. A final source/sequence verification and checkpoint is queued after acquisition.

Defence predictions remain NOT_RUN: verified model-updater routes require GitHub and no permitted complete archive has been verified. See docs/MODEL_ACQUISITION.md. Missing/failed/unsearched remains unknown.

Setup side effect: conda changed the shared /root/.conda/environments.txt timestamp despite registration disabling. Its current bytes/hash/mtime are preserved in evidence/tooling/environment_registry_side_effect.json and environment_registry_current.txt. The list contains only pre-existing paths; no Tree2 environment was registered. Baseline bytes were not captured, so byte identity is unverified. No old analysis/environment payload was targeted or altered. No further conda commands are used.

Live progress is now active in the native PowerShell window TREE 2 - WD - LIVE PROGRESS (three-second refresh). The publisher reads actual stage evidence and worker creation identities; future controllers register state/stages/00.json through13.json, with counters and terminal receipts. The recurring Tree 2 WD stage continuation heartbeat checks every30minutes, advances only scientifically admissible local work, and stays quiet while unchanged. Closing the console leaves workers running. The startup receipt remains historical; state/live_stages.json is the current status surface.

## Completeness-QC continuation (2026-10-26)

The official CheckM2v3 database worker is active; read state/completeness_db_progress.json and its matching launch/exit receipts. It verifies the published MD5 and localSHA256 before committing the archive. Download completion is not environment or scientific-QC readiness. The CheckM2/TensorFlow environment is not installed; a registry-free project-only installer and one-genome resource pilot remain required. Do not run conda entrypoints against the shared registry or increase global WSL RAM. Exact pins, safe admission steps and the limited BUSCO completeness-only corroboration route are recorded in docs/COMPLETENESS_QC_READINESS.md. Biological contamination/completeness remains NOT_RUN until an admitted method actually finishes.

