# Source provenance correction before a production freeze

Audit date: 2026-10-26T17:03:05Z. Acquired source reports audited: **1170**. This is a provisional dataset/source review; no final high-quality isolate panel exists.

All 1170 inspected assembly report files match their acquisition-receipt hashes. **Source integrity can pass while source eligibility is excluded.** Structured source evidence identifies **23 MAGs and 5 SAGs**. These source classes are excluded from the primary isolate analysis. Raw packages, original acquisition batches and QC-review snapshots remain preserved.

The initial metadata normalizer missed genomeNotes/genome_notes derivation notes and some BioSample investigation_type/metagenomic-source fields. Downloaded reports exposed these fields. The corrected normalizer reads affirmative structured MAG/SAG/atypical/uncultivated and culture/isolate evidence in camelCase and snake_case schemas. It does not infer MAG from a project title or a false metagenomic flag. Missing isolate evidence remains a hold rather than a pass. MIMAG/MISAG models and packages are handled explicitly; a mixed MIGS/MIMS/MIMARKS label alone is not a MAG call.

GCA_944324145.1 has genomeNotes='derived from metagenome', investigation_type='metagenome-assembled genome', and a chicken-gut metagenomic source. GCA_982591615.1 has the same structured derivation note, a food-fermentation metagenomic source, and submitter-reported completeness84.03%/contamination1.83% (software checkm). The latter is a submitter estimate, separate from absent NCBI CheckM fields.

## Excluded acquired source classes

| Accession | Source class | Pre-fix metadata QC | BioSample |
| --- | --- | --- | --- |
| GCA_015680865.1 | MAG | QC_PENDING | SAMN16092249 |
| GCA_018883675.1 | MAG | QC_PENDING | SAMN15816781 |
| GCA_018883805.1 | MAG | QC_PENDING | SAMN15816723 |
| GCA_019113985.1 | MAG | QC_PENDING | SAMN15816755 |
| GCA_019114515.1 | MAG | QC_PENDING | SAMN15816736 |
| GCA_019116025.1 | MAG | QC_PENDING | SAMN15816700 |
| GCA_019116645.1 | MAG | QC_PENDING | SAMN15816845 |
| GCA_019117225.1 | MAG | QC_PENDING | SAMN15816838 |
| GCA_019117285.1 | MAG | QC_PENDING | SAMN15816600 |
| GCA_019117445.1 | MAG | QC_PENDING | SAMN15816672 |
| GCA_019118465.1 | MAG | QC_PENDING | SAMN15816663 |
| GCA_944324145.1 | MAG | QC_PENDING | SAMEA110134614 |
| GCA_944326965.1 | MAG | QC_PENDING | SAMEA110134624 |
| GCA_944327185.1 | MAG | QC_PENDING | SAMEA110134609 |
| GCA_946999965.1 | MAG | QC_PENDING | SAMEA111388627 |
| GCA_959028705.1 | MAG | QC_PENDING | SAMEA114096243 |
| GCA_963928705.1 | MAG | QC_PENDING | SAMEA115146529 |
| GCA_963931265.1 | MAG | QC_PENDING | SAMEA115146372 |
| GCA_977882335.1 | MAG | QC_PENDING | SAMEA120789748 |
| GCA_982338535.1 | MAG | QC_PENDING | SAMEA121995264 |
| GCA_982591615.1 | MAG | QC_PENDING | SAMEA122144490 |
| GCF_943192935.1 | SAG | QC_PENDING | SAMEA14418534 |
| GCF_943192955.1 | SAG | QC_METADATA_PASS | SAMEA14418532 |
| GCF_943193025.1 | SAG | QC_METADATA_PASS | SAMEA14418530 |
| GCF_943193105.1 | SAG | QC_METADATA_PASS | SAMEA14418533 |
| GCF_943193185.1 | SAG | QC_METADATA_PASS | SAMEA14418531 |
| GCF_963664355.2 | MAG | QC_METADATA_PASS | SAMEA114301103 |
| GCF_963666195.1 | MAG | QC_METADATA_PASS | SAMEA114301973 |

## Remaining holds and scientific limits

Source provenance counts: {"EXCLUDED_MAG_SAG": 28, "HOLD_SOURCE_UNRESOLVED": 189, "ISOLATE_SOURCE_SUPPORTED_NOT_INDEPENDENTLY_VERIFIED": 953}. Production dispositions: {"EXCLUDED_SOURCE": 28, "HOLD": 223, "SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN": 919}. Source-supported records still require independent genome/taxonomy QC. Candidatus nomenclature curation remains separate from derivation; no Candidatus name alone establishes a MAG. Submitter and NCBI quality evidence remain distinct.

The pre-fix selector and normalized metadata, provisional panels, immutable acquisition batches and review queue were copied byte-for-byte to metadata\history\pre_source_provenance_fix_20261026T164845Z with snapshot_manifest.json before correction. New source exclusions and holds do not rewrite that history, delete acquired packages, or imply defence-system absence. No acquisition was rerun. See qc/source_provenance_audit.json/tsv for per-accession evidence and source hashes. The main selector should be refreshed only after targeted correction checks pass.
