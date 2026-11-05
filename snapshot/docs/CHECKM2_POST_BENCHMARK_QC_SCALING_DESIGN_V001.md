# Post-benchmark stage04 QC scaling: held design v001

This is a source/design proposal, not an implementation, admission or result. The current T1 boundary retains sole compute ownership. No active source, plan, Ready pointer or stage04 row is changed here. Exact inventory/source/receipt hashes and machine-readable gates are in `metadata/checkm2_post_benchmark_qc_scaling_design_v001.json`.

## Current evidence and scope

The provisional panel has1,000 genomes,740 species labels,69 genera and five families.833 records currently have metadata-pass plus source-supported assertions;167 remain metadata-pending, including61 source holds. These are screening labels, not biological eligibility decisions.

The accepted sequence consistency screen contains824 acquired genomes,606 species labels,67 genera and five families. It retained42 cross-label and one within-label ANI review pair,119 strict near-duplicate components and unreported pairs as unassessed. The six subsequently reviewed priority1 nomenclature/type components remain unresolved; no independent genome authentication, relabeling or pruning was granted. Reuse those comparisons and their original manifests; do not recompute the accepted824 screen.

Nine of the833 source-supported metadata-pass records are absent from the frozen screen and presently have no `raw/<accession>` directory. They need a separate immutable acquisition list, verified receipts and a sequence-consistency extension before a panel freeze. Preserve the original acquisition batch and existing ANI outputs. The exact nine accessions are retained in the design metadata; this proposal downloads nothing. The other pending records also stay visible in the species-coverage ledger.

The Abiotrophia method baseline and its format control have accepted feature/closure evidence, with no panel or taxonomy grant. The ten-genome benchmark is still unaccepted in this design. Only seven of its ten accessions belong to the824 screen; the other three are ancillary source-held cases. If the complete benchmark and exact per-row reuse are later accepted, the baseline plus those seven could cover eight screen genomes, leaving816. **816 is conditional, not a count of work currently accepted or completed.** The rewrapped control is not a second biological genome.

## One primary route

After the complete ten-genome benchmark and real closed-unit stop/resume are accepted, prepare one fresh measured batch of **at most20 genomes**. Freeze its membership separately; no membership or launch admission is created here. Use deterministic species-first, family/genus-balanced selection among acquired source-supported candidates, including large-input and fragmented representatives. The proposed total genomic FNA envelope is47,050,840 bytes: twice the fixed ten-input plan's23,525,420 bytes. This limits the next measurement; it is not a biological quality threshold or evidence that this workload will fit.

For each genuinely new input, run the accepted original sequential ProdigalRunner in a cold model-free interpreter, with its unchanged table-selection/fallback rules. Validate and commit the selected FAA, all ten returns, separate DNA metrics and observed unit closure. Then invoke the unchanged stock protein route once for the batch: `--genes --extension faa --threads 1 --lowmem --dbg_vectors --debug`. Keep default fork, the exact matching runtime/overlay/bootstrap and process-local loader setting, private short IPC, durable scratch, and two affinity CPUs. Run one heavy unit at a time.

One cold batch amortizes the existing full-image verification, read-only mount and post-unmount sealing over its genomes, and initializes the models once. Keep every existing integrity check; do not substitute cached readiness for actual mounts, weaken image hashes, create a persistent model service or patch stock algorithms. The existing one-genome quality units took227.887s and231.189s with peak summed RSS1,813,958,656B and1,813,696,512B. Their minimum available RAM was1,489,182,720B and1,477,251,072B. These receipts measure each complete quality invocation; they do not partition model/image/DIAMOND costs, establish biological truth or predict20-genome memory. Query-dependent cosine matrices and activations can grow.

If the next batch passes its actual gates, retain its measured count, total FAA bytes, largest FAA/CDS count and fragmentation envelope as the operational ceiling. Subsequent bounded tranches need their own immutable membership and aggregate budget. Inputs outside that envelope stay pending a separately reviewed stress admission; they are not rejected or silently omitted. There is no automatic escalation beyond20 or a cohort-wide1,000-genome launch. A resource/deadline failure preserves work and stops; it does not split or retry the batch automatically.

## Explicit proposed new-stage budgets

These proposed limits are a **new post-benchmark allocation**. They do not amend or reset the current benchmark's6,000s annotation allowance,600s historical UNKNOWN debit,5,400s new-session ceiling or unused3,600s batch allowance.

| Limit | Proposed next measured batch |
|---|---:|
| CPU affinity / stock CheckM2 threads |2 /1|
| Sampled summed process RSS stop |2,147,483,648B|
| Minimum Linux available RAM |1,073,741,824B|
| Minimum backing-volume reserve |42,949,672,960B|
| Original annotation deadline |600s per new physical unit|
| Maximum new annotation units / aggregate |20 /12,000s|
| One prediction plus all feature validation |3,600s shared remaining time|
| Maximum scientific-unit allocation |15,600s|
| Complete cold session, including auxiliary I/O and cleanup |18,000s|
| Reserved fatal ownership cleanup |40s|

The remaining2,360s at the maximum scientific allocation bounds preflight, manifests, namespace/ordinary closure and sealing. Existing600s image-verification bounds remain inside it. Model startup counts in the prediction unit, not in free overhead. Implementation must derive its nested/outer deadlines consistently and record actual phase durations; these new deadlines are not installed here. No elapsed-budget reset after an outer failure, borrowing between stages, PSS substitution, swap justification, global WSL change or concurrency increase is proposed.

## Evidence, masks and immutable commits

A new minimal, reviewed parameterization of the accepted v002 row validator is required. The current ten-row validator and all active48 sources remain unchanged. Load a SHA-verified own raw pickle once, join exactly the frozen expected accessions, require the ordered21,242-column schema, and validate all21,241 finite numeric features per row. Recompute22 FAA metadata values and1,220 membership features per genome using the corrected raw-copy module versus clipped pathway/category semantics. Retain canonical float64 row hashes and warnings. No fitting across the cohort or score calibration against source metadata is proposed.

Keep each accession's exact five report columns: Name, Completeness, Contamination, Completeness_Model_Used and Additional_Notes. Translation-table decisions and the ten caller returns belong in their separate sidecar. Retain original DIAMOND artifacts and a normalized full twelve-field multiset digest, including duplicate rows. Commit a validated shared batch manifest, then immutable per-genome records referencing their row and batch provenance; the final expected-name/row set must be exact before promotion.

Each genome has separate input, source/holds, sequence-consistency, annotation, prediction, feature-validation, estimate-threshold, taxonomy, coordinate and overall-panel states. Failed/interrupted/not-run outputs and unavailable scores stay null/unknown. A threshold-pass flag is null when its measurement is unavailable. A valid low score is a measured QC result; it does not resolve its source or taxonomy. The project95% completeness,5% contamination and0.5% ambiguous-base targets remain unchanged, together with the no-unresolved-lineage-conflict gate. The three ancillary holds survive every new score. Source CheckM estimates are context, not numerical truth, calibration targets or a substitute for local QC. No QC field supplies a defence negative.

Reuse exact accepted original-input measurements where independently accepted for reuse: accession/FNA and acquisition receipt, caller/options/binary, selected FAA/ten returns/DNA sidecars, runtime/model/database/bootstrap controls, schema/report/features and external closure must match. Retain the measurement's original batch context. Baseline method acceptance alone does not make the row production-eligible. Do not count the control twice, replay an accepted annotation or promote a partial FAA. These QC caller outputs lack retained selected GFF/FNA; stage05 production coordinate annotation remains a separate gate.

## Closed-unit recovery

An annotation is first committed pending context closure; it becomes reusable only after its exact exit0, validation/manifest and externally verified descendant, ordinary IPC/image, unchanged seal and common-lease closure. A future scaling-specific external recovery authority may accept a **known nonzero outer exit** when all reused units and contexts meet those conditions. This is a new design boundary, not a relaxation of active T1 CONTINUE's zero-exit requirement. Unknown unit exits, missing ordinary receipts or forced cleanup remain explicit; disappearance cannot supply a synthetic0. Unresolved ownership retains its handoff/STOP and blocks relaunch until separately resolved.

Persist the prediction once-claim across phases and sessions. A closed successful prediction commits its raw outputs before row validation. If a later file validator or outer observer fails, a separately admitted file-only continuation may use those exact outputs and the remaining shared3,600s. Bind every prior validation budget and terminal receipt as a complete immutable/live-set map; missing elapsed time blocks recovery instead of resetting a debit. A failed or unknown prediction is not an automatic second model attempt. Use the tested same-token cached reader only for optional telemetry, strict reads for essential evidence, retained actual handles and the reviewed creation-matched cleanup policy.

Before any future launch, register the actual Windows owner and creation identity in standard stage04, update within five seconds, and expose annotation and measured-row counters separately through preflight/closure. Terminal diagnostic success leaves whole stage04 pending taxonomy/source/final-panel acceptance. This proposal does not modify that row.

## Remaining gates

1. Actual successful T1 boundary closure, separately admitted continuation, all ten validated benchmark rows, resource fit and complete native/group/ordinary image/lease closure.
2. Root benchmark acceptance and an explicit per-row baseline/benchmark reuse decision.
3. New source/review for the small N<=20 workflow and row-count parameterization, with ownership, LF/transport, budgets, holds and monitor bindings carried forward.
4. Immutable next-batch membership, fresh resources/leases/STOP checks and a separate finite admission.
5. Actual next-batch resource/feature/full-closure acceptance before a subsequent bounded tranche.
6. The nine acquisition gaps, remaining source/type/ANI conflicts, final species-balanced quality eligibility and stage05 coordinate inputs before their respective downstream gates.

No additional diagnostic, helper, annotation, model, runtime import, scientific run, acquisition or executable implementation was performed for this design. All files remain local; GitHub and uploads remain prohibited.
