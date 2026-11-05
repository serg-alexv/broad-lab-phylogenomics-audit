# CheckM1 live display V4.4

The visible display reads the scientific worker's existing
`state/monitor_alternative_qc_v1/current.json` every 30 seconds. It binds the
Root plan and actual native launch receipt from the presentation-only
`state/monitor_checkm1_v1/config.json`. Current process identity is verified by
the exact Windows creation time and the project source command.

CheckM1 measured genomes, batch, batch size, phase, reported phase elapsed time,
reported group RAM and configured CPUs are displayed directly from those
records. The initial queue is 919 genomes in 30 batches: an 18-genome pilot,
then 28 batches of32 and one batch of5. The remaining901 require Root's pilot
review and bound GO; this is an internal scientific gate, not a user approval
wait. No marker search, model, phase, or completion percentage is inferred from
a live PID alone.

Genome processing is shown for a fresh `analyze` report with the worker's
`genome_processing=true` and a matching live registered owner. Preparation,
stale reports, unmatched owners and QA are distinct. Measured counts do not
grant source, taxonomy, quality or final panel acceptance. The older CheckM2
17 accepted estimates remain historical and do not increment CheckM1 counts.
ETA remains unknown until a reviewed CheckM1 benchmark/calibration is supplied.
Old CheckM2 search scenarios and its ETA are not shown as CheckM1 forecasts.

The auxiliary registry and failure-projection readers use direct .NET SHA256,
avoiding the unavailable `Get-FileHash` command. Original V4.3, classifier,
counter-reader, estimator and scientific source bytes are preserved. New
versioned display sources and a replacement visible GUI are used; publisher,
source observer, historical estimator, scientific worker and controller are
not restarted or signalled.

Receipts in `metadata/monitor_checkm1_display_v001` record the exact new GUI
birth, native visible/nonblank console, QuickEdit disabled, two actual frames
about30 seconds apart, and the creation-matched retained-handle exit of the old
GUI only after the new display was visible. Synthetic classification and SHA
fixtures use no genome or model content and start no scientific process.
