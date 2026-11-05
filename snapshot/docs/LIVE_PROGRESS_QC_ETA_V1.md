# QC completion and ETA display

The visible V4.3 PowerShell monitor refreshes every 30 seconds. Its model-free
estimator runs independently of the work chat and writes only monitor sidecars.
It neither launches nor pauses science, changes admission, nor calls an AI model.
QuickEdit is disabled in this console, and redraws retain a last good frame.

The panel distinguishes accepted method estimates, a previously validated saved
feature result, newly feature-validated genomes, full cohort checkpoints, and
newly accepted results. These are not final biological panel acceptance. Saved
validation and reuse in the current session are separate fields; accepted/saved
accession sets are combined without double counting.

The current frozen scope is 919 source-supported candidates: 16 accepted method
estimates, one saved validated result, 897 new genomes in 45 cohorts, and five
historical reviews. The first cohort contains 17 new genomes and one actual
search control. Controls do not increase the new-genome completion count.

A whole-QC finish time remains uncalibrated until a full cohort checkpoint and
its closed successful unit receipts exist. An interrupted search is never a
throughput sample. After a complete cohort, the bulk estimate uses search
seconds per query protein plus residual cohort unit-span seconds per new
genome. It is sample-limited. Historical reviews and final acceptance remain
additional and unforecasted; there is no invented full-queue completion time.
The optional 30/60/120-minute mean-search scenarios correspond to
22.5/45/90 hours for 45 searches alone. They are conditional examples, not
forecasts or confidence intervals. Context and scientific time allowances are
limits, not ETAs. Exceeding a remaining allowance is a display diagnostic only.

Estimator V1.1 reads the public continuation handoff and verifies the bound
launch receipt, native creation identity, launch contract, unique `--input-plan`
argument and expected SHA256 flag. It derives the native output directory from
the registration. Before a runtime bulk request exists, bound canonical plan,
campaign data, accepted registry, and saved checkpoint preserve the frozen
campaign totals. The scientific output directory remains explicitly pending
until an actual request with matching parent-plan and output-root bindings
appears. Its name need not match the native owner's version or folder.

If binding or path resolution fails, current campaign counts are null/unknown
and a new-worker/path-unresolved status is recorded. The existing GUI schema
guard shows its unavailable-observation block rather than interpreting null
arithmetic as a zero result. No previous attempt supplies a new owner's phase,
failure, speed, or inferred clean exit. Missing processes retain unknown closure.
The protein-count input is bound to this frozen campaign; a changed campaign
needs an updated, bound timing input before its forecast is interpreted.

Presentation pointer: `state/monitor_presentation_current.json`.
Estimator snapshot: `state/monitor_qc_eta_v1/current.json`.
Estimator input: `state/monitor_qc_eta_v1/input.json`.
Bound protein/timing evidence: `state/monitor_qc_eta_v1/timing_input.json`.
Last rendered frame: `state/monitor_display_v4_3/display_last_frame.txt`.
Display health: `state/monitor_display_v4_3/display_health.json`.

Deployment receipts preserve exact process births, source hashes, native
visible-console observations, and two real updates about 30 seconds apart.
The old GUI remains preserved and minimized. V1.1 replaces only the estimator;
the old estimator has a retained-handle actual exit receipt. Publisher,
collector, scientific worker, and event controller remain untouched.

Validation uses synthetic metadata only: interrupted-phase rejection,
features-versus-checkpoint distinction, protein weighting, suspended finish
clock, budget diagnostics, a launch-only successor with no optional handoff
fields, canonical totals during preflight, unrelated output-folder names,
and hash drift producing unknown counts. No fixture starts science or reads
genome/model content.
