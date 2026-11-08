# Tree 2 continuation gates — 8 November 2026

This is a working audit note, **not** a scientific acceptance or ledger promotion. The frozen `main` checkpoint is commit `7d0622402fc00c493b18b7d630f52bae2a733d47` (5 November 2026).

## Evidence established directly from published GitHub assets

- Full-panel tree: 900 taxa, 54 aligned protein markers, 13,071 amino-acid positions, IQ-TREE 3.1.4 using `LG+F+G4`, 1,000 UFBoot / 1,000 SH-aLRT.
- The frozen ledger records `CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED=165`, `RESERVED=20` for C009, `NOT_RUN_UNKNOWN=734`. This is a **historical** status, not a contradiction of work reported after the release.
- C009 archived results: 20 genomes, 40 phases, 194 PADLOC plus 143 DefenseFinder model-relative calls, 33,720 typed HMMER searches. [The GitHub Actions QA run](https://github.com/serg-alexv/broad-lab-phylogenomics-audit/actions/runs/42485838737) verified the pinned 93,641,823-byte archive (SHA-256 `ff49a11de531ecce280df61d8213dd15eca62d66af17392bb0b6a3c97c14a2dd`) and independently rehashed 33,720 raw outputs. The run was successful; C009 **was not** promoted.
- The original `full_tree.log` states: "**735 sequences failed composition chi2 test (p-value<5%; df=19)**" among 900. This warrants model-adequacy / compositional-heterogeneity scientific review, not automatic invalidation or acceptance.

## Subsequent working state reported in prior conversation (NOT included in frozen GitHub release)

- As of 8 November: 734 additional genomes (729 tree tips and 5 held) reported searched successfully by both PADLOC and DefenseFinder; 1,468 / 1,468 file-verified phases, no reported review flags, Docker exit 0.
- Unified working tables reportedly contain 919 genomes, 13,941 model calls, and 28,525 supporting gene rows, including 11,002 calls from the new 734.
- Consolidated outputs in `tree2_stage9_tables_v1`: `all_919_genomes.tsv`, `all_13941_model_calls.tsv`, `all_supporting_genes.tsv`, `provisional_900_tip_annotation.tsv`, `cross_detector_overlap_candidates.tsv`. Their **bytes are not evidenced in the frozen GitHub release**.
- Overlap graph: 4,243 pairs; 3,457 identical, 597 high, 189 partial; 3,413 distinct identical gene-set groups comprising 3,391 one-to-one and 22 multi-model groups; 786 nonidentical pairs require review. No biological deduplication inferred.
- Six historical accepted genomes reportedly lacked coordinate inputs in the later import; rescue completion was not demonstrated in prior conversation.

## Acceptance gates (distinct, non-substitutable)

1. **Provenance synchronization.** Secure versioned, byte-verified 8 November consolidated outputs and raw receipts in a new release/workspace. Do not overwrite the 5 November snapshot or misstate it as up to date.
2. **C009 file QA versus historical process closure.** Raw HMMER integrity and saved stock-report crosschecks passed. Historical WD process/lease/namespace closure and original installed runtime/model source-file bytes remain unverified. Do not set original ledger acceptance without a defensible, separate closure/provenance disposition. Save any epistemic limits explicitly.
3. **Coordinate rescue and typed gene identity.** Resolve six missing coordinate inputs before final genome-locus mapping. Preserve unresolved rows as missing/unknown.
4. **Cross-detector overlap interpretation.** Annotate equivalence, nested and distinct hits without silent deletion or unjustified 1:1 system claims.
5. **Phylogenetic biological QC.** Investigate 735 composition chi-square failures, taxonomic and orthology holds, marker selection, rooting and model/topology sensitivity. Keep 900-tip tree labelled computationally valid but not biologically accepted until reviewed.
6. **Reproducibility package.** Use Lactococcus 1024 V4 as primary pattern plus phage 1374 accession/fingerprint verification. Separate `source_integrity`, `figure_reconstruction`, and `analytical_reproduction` into independently executable PASS/FAIL/UNAVAILABLE gates.

## Immediate next executable work independent of WD

- Extract a 900-tip per-sequence composition diagnostic from the pinned IQ-TREE log; quantify and group the 735 failures by available source taxonomy; identify models and marker/taxon subsets for bounded sensitivity tests.
- Maintain all pre-existing tree and defense source outputs read-only.
- Do not rerun 734 PADLOC/DefenseFinder predictions merely because the post-release table bundle is not currently available in GitHub.
