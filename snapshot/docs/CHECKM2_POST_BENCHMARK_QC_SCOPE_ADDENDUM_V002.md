# QC scaling scope addendum v002: empirical coverage of deferred species

This source-only addendum clarifies the priority subset in V001. It preserves V001 document SHA256 `dc2169f7ce76374253882105bf29cee2ccfad3cfe72c4b66bf75dffa22ef02dd` and metadata SHA256 `5a961ff145719710c64b12a7d017e19cc37f17fa57db1e5adcb9c2c6489be701`. No source, status, budget, admission, genome or QC result changes here. Exact counts, 95 accession IDs, 92 priority taxids and source hashes are in `metadata/checkm2_post_benchmark_qc_scope_addendum_v002.json`.

## 824 is a priority subset, not the biological eligibility boundary

The acquired source audit contains 1,170 records: **919 source-supported awaiting biology, 223 HOLD and 28 excluded from the isolate-source scope as MAG/SAG**. These are source dispositions, not measured biological pass/fail calls.

Of the 919, the existing DNA consistency screen contains 824 genomes and 606 species-level labels. The other 95 genomes cover 93 labels; one label is also in the 824 screen, while 92 are absent. Thus the supported acquired universe covers **606 + 93 - 1 = 698 labels**. The 95 also contain two genera absent from the 824 subset: Daquilactobacillus and Hutsoniella. Label counts do not establish authenticated species or final eligibility.

The 95 can supply one record for each of 92 otherwise-unscreened labels, followed by two additional strains within those labels and one record of an already-screened label. They must remain in empirical-QC and species-coverage accounting. V001's conditional 816 remaining rows applies only to 824 after eight possible accepted-result reuses. The corresponding conditional full 919 remainder is 911. Neither number is an actual accepted/reuse count.

## Their current state is QC_PENDING

| Existing pending metadata context | Genomes |
|---|---:|
| Contamination metadata missing only |82|
| Source ANI status Inconclusive only |11|
| Both |2|
| Total |95|

Consequently 84 lack source contamination metadata and 13 have Inconclusive source ANI status. All 95 are exactly `QC_PENDING`; none has a recorded metadata exclusion or sequence-rejection entry. None is deferred here for a source completeness value below 95% or a known contamination value above 5%. Missing values and Inconclusive status are unknown context, **not biological failures**.

The 95 existing acquisition receipts still match their audited SHA256 hashes and record acquisition/FASTA-validation PASS. All contain recorded ambiguity fractions at or below 0.5%; the maximum is 0.4126420801%. These are existing technical observations, not a new sequence screen, biological-QC pass or taxonomy validation. No independent completeness/contamination computation or recorded independent biological failure exists for these 95 in the inspected records. Future real integrity/format/technical failures require their own evidence and per-input repair/review; they do not by themselves establish species ineligibility.

## One bounded empirical triage lane, using the existing proposal

After full benchmark/resource/stop-resume acceptance and source review, prioritize a deterministic family/genus-balanced prefix of the 92 otherwise-unscreened labels in the already-proposed next fresh batch of at most 20. Use one accession per such label before optional additional strains. Continue the remaining labels in separately admitted finite batches within the actually measured envelope; do not wait for discretionary strain work across all 824 to finish.

This uses V001's single primary original-caller/stock-protein route and the **same proposed allocation**, not another diagnostic or extra quota: at most 20 annotation units of 600 s, 12,000 s annotation aggregate, one 3,600 s shared prediction/feature-validation unit, and unchanged two CPUs, 2 GiB summed RSS, 1 GiB headroom and 40 GiB reserve. V001's FNA envelope, cold-session cap, full closure, no-replay, unknown masks and new-source/admission requirements remain. No active ten-benchmark budget is amended. Actual membership and execution authority remain null.

Run independent measurements even when source contamination is missing; do not require that metadata value as a biological admission prerequisite. A later reviewed sequence-consistency/ANI extension must preserve the 824 comparisons and treat unreported pairs as unassessed. The 13 Inconclusive source cases keep taxonomy unresolved until that separate evidence is reviewed. Fresh model scores are estimates, not truth, calibration targets or taxonomic decisions. Every genome retains separate input, prediction/feature, source, taxonomy and final-eligibility masks. No species is dropped solely on metadata quality values or their absence.

## The 223 holds remain unresolved, not negative

The 223 HOLD records cover 183 source species labels, which can overlap the 698 supported labels.189 have unresolved source status;34 have a supported source assertion but another review hold.23 of those 34 are held solely by the legacy metadata-QC exclusion. Such legacy quality concerns may inform later separately admitted empirical review and explicit curation; they cannot become permanent biological exclusion from metadata alone.

All 223 retain their individual holds and unresolved source/final-eligibility states. Valid completed measurements retain their actual values and availability masks; unmeasured quality stays unknown. Per-record source/identity/taxonomy review precedes any appropriate empirical follow-up. The three ancillary benchmark cases illustrate this separation: a new score can inform review but cannot clear their holds by itself. No withheld, failed or unsearched record becomes a biological negative, defence zero or an omitted species without a recorded eligibility decision.

The nine currently unacquired metadata-pass/source-supported candidates identified in V001 also remain pending input acquisition and later independent QC. This addendum neither downloads them nor promotes them. All final species-balanced panel, source/type, lineage, quality and production-coordinate gates remain open.
