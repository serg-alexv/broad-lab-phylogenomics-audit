# DNA sequence consistency QC

This independent screen ran on824 current-panel genomes with acquired genomic FASTA, a matching SHA256 receipt, source-supported status and QC_METADATA_PASS metadata. They represent606 species labels. MAGs,SAGs,source holds and metadata exclusions were not admitted. Source support and metadata screening do not grant biological-QC acceptance.

Installed skani0.4.0 was run with2 threads, default compression125, sparse/detailed output, diagonal/self comparisons and ANI confidence intervals. Minimum emitted one-direction AF was15%. The100-genome resource pilot passed before the full824-genome run. The full run completed in15.28seconds with sampled peak group RSS319,844,352bytes(~305MiB), exit0 and queried-empty owned process group. No global resource settings changed.

The full sparse output contains824 self rows and1,156 non-self rows from339,076 potential non-self comparisons. Unreported pairs remain unassessed; they are not converted to zero ANI or biological absence.340 genomes have a non-self match to a metadata-designated type-material genome with ANI>=95% and both directional AF>=65%. This is review evidence, not independent nomenclatural adjudication, and self matches do not validate a label.

Review flags use ANI>=95% with AF>=65% in both directions for cross-label high-ANI candidates, and ANI<95% with the same AF condition for within-label candidates. There are42 cross-label and1 within-label pairs. The within-label case is Streptococcus sanguinis:GCF_013343115.1 versus GCF_900475505.1, ANI94.87%, AF83.82%/86.08%. Neither label was changed and neither genome was removed.

There are127 pairs with ANI>=99.99% and AF>=65% in both directions, meaning almost-identical aligned DNA under that coverage condition. A stricter whole-genome near-duplicate review uses AF>=95% in BOTH directions;119 pairs meet it, forming119 two-genome connected components. High ANI does not establish identical accessory/defence content; no automatic pruning occurred.

The95% ANI threshold is a review convention informed by broad genome comparisons, not a universal species rule. [Jain et al.,2018](https://www.nature.com/articles/s41467-018-07641-9); see the sampling/interpretation critique in [2021 sampling critique](https://www.nature.com/articles/s41467-021-24128-2). Skani's underlying ANI/AF method is described in [skani primary paper,2023](https://www.nature.com/articles/s41592-023-02018-3). The AF65% and strict-near-identity thresholds here are explicit project review choices, not claims that those papers establish them.

Artifacts are in analysis/sequence_qc/d64e016face251f1/. input_manifest.json binds each input FASTA hash and exact metadata; commit.json retains the actual scientific-execution controller hash, and controller_source_at_execution.py preserves those bytes. artifact_manifest.json hashes the21 output/source files. full_cohort/ani.tsv retains raw estimates and uncertainty columns. Pair/genome flags, strict_duplicate_curation.json and process/resource/exit receipts are separately recorded. state/sequence_qc_progress.json reports phase progress and actual worker identity. Resume verifies input/output hashes and skips existing scientific comparisons; no accepted upstream annotation or genome file is altered.

Completeness/contamination,final sequence taxonomy,production marker validation,trees and defence predictions remain NOT_RUN or unaccepted. This screen alone does not admit the production pipeline past those gates.


A source-only follow-on review is documented in docs/SEQUENCE_QC_SOURCE_REVIEW.md. It preserves all170 flags and119strictduplicate components, with explicit type-status distinctions and source-identity evidence; no taxonomy acceptance or pruning occurred.

