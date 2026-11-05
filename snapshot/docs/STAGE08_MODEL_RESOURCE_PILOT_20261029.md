# Stage08 bounded model and resource pilot

The next primary computation uses the accepted accession-labelled matrix at
`analysis/phylogeny/full900_conservative54_v001/supermatrix.faa` unchanged:
900 genomes, 54 putative universal single-copy loci, 13,071 amino-acid columns.
The closed Stage07 authority is
`metadata/stage07_conservative900_54_v001/Root_ACCEPTED_COMPUTATIONAL_MATRIX.json`.
Its accepted alignments, matrix construction and independent validation are reused.

The exact local plan is
`metadata/stage08_model_resource_pilot_v001/Root_plan.json`.
Stock IQ-TREE 3.1.4 first runs TESTONLY on the complete matrix with the restricted
LG/WAG/JTT candidate set, empirical frequencies, four gamma categories and BIC.
It then performs one bounded fast search with the best model from that limited set.
This measures actual full-matrix resource use and limited model fit. It does not
establish final model adequacy, an accepted partition scheme, branch support or a
production tree. The original 54 locus partitions remain available unchanged.

One stock thread uses Linux CPU2; the native owner is confined to CPUs0,2.
IQ-TREE receives a 1400M memory limit. Summed owned Linux RSS plus private temporary
RAM must stay at or below 1.75GiB, with a separate 128MiB native reservation and
the unchanged 2GiB total ceiling. Linux available memory must remain at least
1.25GiB, with at least 40GiB backing disk free. Each scientific phase has 3600s,
the cohort has 7200s science and 9000s cold time, and the plan records an absolute
deadline. Actual resource failures, elapsed debits and checkpoints are preserved.

The reviewed detached launcher and existing genericV3 dispatcher retain the exact
new native identity before scientific work is permitted. Every successful phase
commits its exact input, command, typed actual exit and durable IQ-TREE artifacts.
No automatic retry, --redo, --undo or consumed-claim reset is permitted. Local
Stage08 presentation updates every 30 seconds. The next real worker event must
establish native/WSL/child/group/private namespace/IPC/FD/lease closure and validate
saved outputs before a separate full-inference admission and Stage09 independent QC.

The 19 genome holds, three alignment-sensitive locus holds and nine composition
flags remain explicit. Final orthology, independent taxonomy, eligible-species
rescue, expanded-seed robustness, model adequacy and high-quality panel acceptance
remain owed. No gene is removed to produce a desired taxonomy. Both the final
full-panel and representative-panel conventional trees need separate validated
receipts. The completed five-genome defence pilot is preserved, and further
defence batches are deferred under the current primary phylogeny order.


The first invocation actually closed native1/WSL1/IQTREE2 at the argument parser:
this pinned binary advertises --mfreq in help but implements -mfreq/--freqs.
Read-only binary-literal evidence and actual closed failure are preserved in
`work/stage08_repair_f339/`. The explicitly reviewed V002 continuation changes
only that option spelling. Current plan/admission are in
`metadata/stage08_model_resource_pilot_v002/`. Old claims, STOP and failure
outputs remain unchanged. The0.586675717s scientific and1.096490165s measured
cold debits are retained; available model-test/science/cold allocations are
reduced and the original absolute deadline is unchanged. No successful
scientific phase or accepted Stage07 work was replayed.


V002 reached computation but the RSSguard stopped it: native1/WSL1/IQTREE-15.
The original900leaf parsimonytree and partialgziptext ModelFindercheckpoint
were validated and preserved. V003 lowers only the stock internal cache target
to700M,uses the saved parsimony startingtree,and seeds the unchanged checkpoint
bytes into a fresh outputprefix for stockresume. HardRSS+RAM/native/headroom/disk
and scientific models/thresholds stay unchanged. Resourcefatal cleanup now sends
creation-bound pidfdTERM immediately; ordinaryfatal retains30/5/5 cleanup.
The guard records the fatal sample and fullownedunitRSS in30second presentation.
Current exact plan/admission: `metadata/stage08_model_resource_pilot_v003/`.
Prior science71.68908241200552s and measuredcold72.59322599100414s remain consumed,
with the same original absolute deadline. There is no accepted model-fit/tree
phase to replay; stock checkpoint restoration still requires actual output
validation at the next real event. Final inference/model adequacy remain owed.
