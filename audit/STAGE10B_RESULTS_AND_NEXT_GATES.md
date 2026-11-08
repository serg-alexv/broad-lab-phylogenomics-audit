# Stage 10B: original-model molecular evidence and provisional dispositions (2026-11-08)

**Status: PARTIAL SCIENTIFIC DISPOSITION; NOT a final biological defence-system census.**

This review uses frozen, original saved HMMER evidence for six of the fifteen high-priority accession/component groups identified in Stage 10A. It does not alter any of the original 13,941 model calls, promote C009, deduplicate biological systems, infer functional activity, or accept final figure rings. The historical baseline is commit \`7d0622402fc00c493b18b7d630f52bae2a733d47\`.

## Executed verification

- [Successful Stage 10B original-source extraction and gene-role join](https://github.com/serg-alexv/broad-lab-phylogenomics-audit/actions/runs/42491083781) — GitHub Actions, source script \`audit/stage10b_extract_original_hmmer.py\` on the separate evidence branch.
- The C003, C005, C006, C007, original C008/recovery, and data-provenance release archives passed original **SHA-256** comparison.
- **12 of 12** targeted PADLOC/DefenseFinder phases retained source-bound artifacts; all **50,862** phase-artifact references matched their saved sizes and SHA-256 hashes (plus phase and input files inspected; no missing/mismatched phase artifacts).
- **10,116** raw HMMER output files and matching receipts inspected; **1,359** PADLOC target-mapped profile rows retained; **105** original DefenseFinder gene-level stock-report rows joined using preserved \`protein_identity_map.json\` maps.
- **Correction to an earlier preliminary log:** 208,987 is the count of all non-comment text lines captured from HMMER \`*.raw\`, **including narrative \`-o\` reports**; it is **not** the count of valid hit rows. Use only the target-mapped PADLOC/DefenseFinder figures above for scientific interpretation.
- Six-source-locus derived table plus 26 diagnostic profile rows reproduced byte-for-byte on repeat local execution. These are interpretive, evidence-preserving review outputs, not a whole-project rerun.

## Scientific dispositions

See [machine-readable TSV](STAGE10B_SIX_LOCUS_PROVISIONAL_DISPOSITIONS.tsv) for the exact accession, cohort, representative HMMER i-E-values, source-predictor context, tree inclusion and status.

| Source group | Evidence-supported disposition | Biological system count |
|---|---|---|
| \`GCF_001870205.1\` (C003), \`GCF_002847845.2\` (C005), \`GCF_030222485.2\` (C008) | Type II-A favored over DefenseFinder's narrower II-C call: original PADLOC Cas9/Cas1/Cas2 **plus Csn2** domain hits in adjacent excluded proteins. | Not independently accepted; CRISPR arrays not assessed |
| \`GCF_026131645.1\` (C007) | Type III-D strongly favored. Cas10d, Cas5-III-D, Cas7-III-D profiles agree; the **original DefenseFinder stock output ALSO contains a five-gene III-D call**, alongside an additional two-gene III-B candidate. These are model hypotheses, not two established systems. | Not independently accepted |
| \`GCF_024701915.1\` (C006; held outside the 900-tip tree) | PADLOC Type-II MTase/REase signals overlap a **single-gene** DF McrBC-family model hit. Full McrBC complex and the number of biological systems cannot be established from this call. | Unresolved |
| \`GCF_900129415.1\` (C006) | Distinct strong mREase-IV and Type-I HsdM/HsdS/HsdR profile signals occupy a shared extended region. DF Type-I additionally cross-hits the mREase-IV protein with a weaker Type-I REase profile. Do not merge these model labels or claim two functional systems. | Unresolved |

Canonical source-gene membership and architecture were previously audited in the Stage 9/10A 919-genome dataset. This molecular-evidence pass adds original HMMER and MacSyFinder model evidence; it does **not** independently verify array presence, expression or activity.

**Mechanistic interpretation:** Csn2 is a characteristic Type II-A adaptation protein; Type II-C usually has a three-gene Cas9/Cas1/Cas2 operon. See [Classification and evolution of type II CRISPR-Cas systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC4041416/). Cas10 and subtype-specific Cas5/Cas7 profiles support the Type III-D interpretation, but subtype assignments remain provisional pending full biological review.

## Next bounded analysis

- The **other nine** highest-priority accession/component groups are part of the newer 734-genome local stock-output import, **not** the frozen 5 November GitHub release. Their original raw HMMER/model role evidence is not currently represented by this source-extraction branch. Do not claim these nine are resolved or repeat the entire 919-genome search.
- Retrieve only those nine groups' source-scoped HMMER/model roles when exact saved outputs become available. Alternatively, perform a separately versioned and explicitly flagged *targeted new* model check on the pinned proteins and models—not as a substitute for the original historical receipts.
- Then propagate the evidence-level biological review dispositions to the **900-tip provisional** matrix, while retaining all raw 13,941 calls and the 4,243 cross-detector overlap edges.
- Finally assemble one archive with the complete scientific provenance and executable acceptance gates, using the previously audited Lactococcus 1,024 and phage 1,374 archive standards. No user-side intermediate downloads are required.

## Working source fingerprints (not claimed to exist in this repository)

The original uploaded and generated ChatGPT Stage 9/10A sources used for this review had SHA-256 digests:

- \`TREE2_919_QA_INPUTS.zip\`: \`939f09f7d1bec587126a6fcd5e4fd3332a6481bce16b7170f12fb8b3cdb7eb9d\`
- \`TREE2_STAGE9_919_PROVISIONAL_QA_MATRIX_REPRO_V2_20261108.zip\`: \`80d5d832cb14bd899e7636ebe81c63f4bed9ad6eecec28602b6849096e1d17c4\`
- \`TREE2_STAGE10A_83_PRIORITY_LOCUS_REVIEW_REPRO_20261108.zip\`: \`69b956ce55d9565bc2d2e4dc9b867d776fa3ce0a5a4bb183c751b98ad2a521dd\`
- GitHub Actions Stage 10B target evidence artifact ZIP: \`3403c6abc67b025cd3b943c1373fc6408722615a9c51b920ef46befc76c21c7f\`

These independent fingerprints support a later single consolidated reproducibility release. They do not imply that the three uploaded interim archives are already hosted on GitHub.
