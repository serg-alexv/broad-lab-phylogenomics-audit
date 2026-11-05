# Alternative QC preparation display

The current display distinguishes preparation of the CheckM1 Lactobacillales
assessment from the closed CheckM2 shared-control failure. No alternate pilot
PID, completed genome count, rate, or finish time is assumed during preparation.
The visible console, estimator, publisher, and source observer keep their
existing processes and 30-second cadence.

Registry v007 records 17 unique accepted method estimates: 16 earlier estimates
plus the saved result, which is now accepted and already included. Displaying
the saved result separately must not increase that total to 18. Final source,
taxonomy, quality and panel decisions remain separate.

The old CheckM2 shared search and raw validation completed successfully, but the
required full raw-control equivalence failed. Native/WSL/helper exits 2/1/1 and
full resource closure remain retained. Its 45-cohort counters describe the
previous frozen scope; they do not describe an alternate-method pilot.
The previous numerical search scenarios are suppressed for the new method.

The existing source observer reads `state/preparation_gates_v2.json` and watches
the real setup progress/receipt paths under `metadata/checkm1_taxon_setup_v001`.
Setup extraction is dependency preparation, not genome processing. Root owns the
authoritative stage04 row and will provide an exact native identity if a
reviewed finite pilot starts.

`state/monitor_alternative_qc_v1/current.json` is a presentation contract draft.
It uses null for unknown pilot completion, elapsed science, ETA, admission and
owner. A future current-worker projection should add method, bound plan and
launch references, exact creation identity, actual phase, known completion
denominator, receipts, and any independently calibrated rate. Its `genome_processing`
flag must require actual matching worker evidence. This draft does not launch
or supervise anything and is not an admission or scientific result.

The old V4.3 GUI reported `Get-FileHash` unavailable in its auxiliary readers.
The subsequent V4.4 display fixes this with direct .NET SHA256 in new versioned
sources. It shows actual CheckM1 progress separately from the 17 historical
CheckM2 estimates; see `LIVE_PROGRESS_CHECKM1_V4_4.md`.
