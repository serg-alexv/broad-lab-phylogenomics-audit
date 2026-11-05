# TREE 2 - WD LAB phylogenomics and antiphage defence systems

This is a NEW, isolated analysis on host WD, created 2026-10-26. The user explicitly authorized execution, including public NCBI discovery and controlled acquisition. All project artifacts stay on WD. No GitHub access, uploads, old panel reuse, or laptop Tree 1 changes are authorized in this run. Conventional full and representative trees precede any 3D work.

Primary live scope: NCBI Lactobacillales taxid 186826, with dynamic current family/genus/species lineages. Bifidobacteria are outside this order and are not silently included. Ingroup includes Enterococcus; old exclusions are not inherited. Approximate goal: 1,000 quality-checked, diverse, species-balanced genomes. The confirmed sampling contract is every eligible species first, then balanced strain sampling near1,000; production eligibility still requires the recorded quality gates.

See docs/STAGE_PLAN.md for stages/gates, docs/SOURCES.md for scientific and software sources, metadata/ for source snapshots and provisional sampling, evidence/ for host evidence, state/ for actual execution state, raw/ for committed per-genome data, and manifests/ for SHA256 snapshots. A presence ring means a complete PREDICTED defence system under a pinned model, never experimental validation. Unknown, failed and not-run remain unknown.

## Execution and checkpoints

Use scripts/discover.py for metadata catalogs/taxonomy and scripts/select_panel.py for provisional selection. Use scripts/acquire.py for controlled acquisition. Absolute Python interpreter is recorded in config/runtime.json. Completed artifacts are checked against receipts before skipping. Source metadata are immutable per query; changed input hashes stop execution. A partial transfer is not committed. STOP is requested by creating state/STOP; remove this file only when intentionally resuming. Rerun the same command to resume. No scientific computation is automatically relaunched merely because a PID is missing.

OS-backed locks guard each controller, and exit receipts record graceful termination. Abrupt process death releases the OS lock; resume also verifies committed hashes. An immutable full manifest is a checkpoint, not a claim that all scientific stages passed. Acquisition stop/resume and integrity checks have completed; production biological QC remains gated. The visible PowerShell display refreshes every30seconds. Continuation and failure recovery are project-local and event-driven; recurring app-chat heartbeat prompts were revoked and deleted. See state/local_continuation_current_runtime.json, state/live_stages.json and docs/LIVE_PROGRESS.md for actual current ownership and monitoring.

Sampling clarification resolved: the user confirmed every eligible species first, then balanced strains near1,000. This confirmed contract governs the run.

The user also explicitly authorized a whole-genome automatic QC queue, not one batch at a time awaiting reminders. See metadata/tree2_qc_campaign_queue_v001.tsv and its JSON/manifest, state/qc_campaign_queue_v1/intent.json and docs/WHOLE_QC_QUEUE_AUTOMATIC_CONTINUATION_V001.md. The current source-supported scope is919candidates:14verified method results reused and905remaining repair/review/processing entries. Each accepted closed cohort automatically produces the next disjoint proposal; queue exhaustion requires full scope/registry reconciliation. The current persistent consumer is identified by state/local_continuation_current_runtime.json.


