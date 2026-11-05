# Sampling review before production-panel freeze

Review date: 2026-10-26. Source selection snapshot: 2026-10-26T16:12:57.742629+00:00. All selections remain provisional; no final high-quality panel or species coverage claim is made.

## Coverage and screening results

The refreshed corpus contains 11,355 versioned accessions. The provisional 1,000-genome panel represents 767 species-level taxids: **733 other species-level taxa and 34 Candidatus taxa pending separate nomenclature/source curation**. Every selected Candidatus row is already QC_PENDING. These categories are not a claim that all remaining names or genomes have been independently verified.

The original priority catalogs left 113 species with only excluded candidates. Overlapping species-level reasons were completeness below 95% (74 species), contamination above 5% (49), more than 200 contigs (14), and N50 below 20kb (5); other reasons included source/taxonomy conflicts. Broader per-species retrieval recovered acquisition-eligible candidates for 8 species (6 with metadata passes and 2 with pending QC). **105 species still have no acquisition-eligible candidate under current screening.** None of these exclusions establishes biological absence.

Among those 105 species, **31 have complete/chromosome assemblies** and form a priority independent-QC review stratum. After hard source gates and an affirmative culture/isolate provenance requirement, the immutable review queue contains **23 genomes, one per species**. The remaining 8 species are held back for the reasons below. This is a conservative acquisition-review queue; it does not promote any genome into the production panel or alter its 95%/5% gates.

## Candidatus curation policy

Candidatus is a nomenclature status and does not by itself establish that a genome is MAG, SAG, uncultivated, or poor quality. Some selected records explicitly describe isolates: GCF_017316025.1 / [SAMN18075559](https://www.ncbi.nlm.nih.gov/biosample/SAMN18075559) (Enterococcus myersii, sample_type=isolate, sand filtrate); GCF_017315945.1 / [SAMN18075572](https://www.ncbi.nlm.nih.gov/biosample/SAMN18075572) (Enterococcus courvalinii, sample_type=isolate); and GCF_017316105.1 / [SAMN18075568](https://www.ncbi.nlm.nih.gov/biosample/SAMN18075568) (Enterococcus ikei, sample_type=isolate). Other source descriptions are ambiguous, such as GCF_017316185.1 / [SAMN09399635](https://www.ncbi.nlm.nih.gov/biosample/SAMN09399635) (water; no explicit sample_type) and GCF_009933175.1 / [SAMN05199424](https://www.ncbi.nlm.nih.gov/biosample/SAMN05199424) (Whole organism).

Keep these 34 taxa in an ancillary pending-curation stratum. Preserve existing acquisition snapshots and downloaded files. Before a production freeze, curate nomenclature, culture/derivation provenance, taxonomic identity and independent genome QC; reject demonstrated MAG/SAG/uncultivated or unresolved production entries under the primary isolate contract. Do not label Candidatus as biological absence or silently count the group as formally curated species. The API formal-name flag is omitted for the inspected examples and cannot supply affirmative nomenclature evidence here.

## Method-sensitive cutoff risks

Closed assembly status is not an independent quality guarantee, and a CheckM estimate is not a direct measurement of missing DNA. Examples requiring review include complete Lactococcus protaetiae GCF_006965445.1 (83.87% completeness; genus marker set), Acetilactobacillus jinshanensis GCF_055764315.1 (91.98%; family marker set), and Melissococcus plutonius GCF_059745495.1 (94.05%; family marker set, contamination field omitted). The CheckM paper describes lineage-related estimation limitations, including underestimation in reduced lineages. This establishes a potential method-sensitivity mechanism, **not its cause in these LAB genomes**. [Parks et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4484387/).

Use CheckM2 or another justified independent completeness/contamination method, sequence-derived QC, taxonomic checks and marker-level review to distinguish estimator behavior from actual defects. CheckM2 provides a different prediction approach; agreement or disagreement still requires interpretation. [Chklovski et al., 2023](https://pubmed.ncbi.nlm.nih.gov/37500759/). Keep omitted contamination values unknown. Do not lower production cutoffs silently, substitute a complete label for QC, or declare excluded species absent. Fragmentation cutoffs also affect defence-system detectability and should be treated as explicit methodological choices.

## QC-review queue

Queue: metadata/acquisition_qc_review_only.json. Status: QC_REVIEW_ONLY; independent_biological_qc=NOT_RUN; acquisition not launched by this review. Original exclusion reasons and NCBI CheckM source/version/marker-rank evidence are retained per entry. Source support consists of type/culture-collection metadata, an explicit isolate field, or a cultured/clinical BioSample model; it is not independent proof of purity.

| Species | Review accession | NCBI completeness % | NCBI contamination % |
| --- | --- | ---: | ---: |
| Lacticaseibacillus casei | GCF_000829055.1 | 86.97 | 1.55 |
| Carnobacterium maltaromaticum | GCF_009738125.1 | 98.22 | 10.66 |
| Melissococcus plutonius | GCF_060436625.1 | 92.99 | None |
| Pediococcus parvulus | GCF_044051695.1 | 90.73 | 8.03 |
| Enterococcus raffinosus | GCF_025402795.1 | 98.37 | 8.18 |
| Pediococcus inopinatus | GCF_002982135.1 | 91.18 | 9.73 |
| Aerococcus sanguinicola | GCF_001543145.1 | 85.75 | 6.89 |
| Aerococcus urinaehominis | GCF_001543245.1 | 82.61 | 8.94 |
| Vagococcus carniphilus | GCF_014397115.1 | 96.72 | 6.48 |
| Tetragenococcus koreensis | GCF_003795145.1 | 90.36 | 8.74 |
| Pediococcus siamensis | GCF_047220215.1 | 89.57 | 6.47 |
| Tetragenococcus osmophilus | GCF_003795125.1 | 88.98 | 8.14 |
| Acetilactobacillus jinshanensis | GCF_004359375.1 | 91.98 | 1.33 |
| Oenococcus sicerae | GCF_004102045.2 | 89.83 | 2.52 |
| Lactococcus allomyrinae | GCF_003627095.1 | 93.72 | 1.9 |
| Lactococcus protaetiae | GCF_006965445.1 | 83.87 | 2.08 |
| Vagococcus coleopterorum | GCF_011303955.1 | 88.96 | 1.7 |
| Xylocopilactobacillus apis | GCF_033095965.1 | 92.68 | None |
| Xylocopilactobacillus apicola | GCF_033095985.1 | 92.82 | 1.96 |
| Fructobacillus americanaquae | GCF_024029775.1 | 91.7 | 0.33 |
| Vagococcus intermedius | GCF_029144185.1 | 95.35 | 5.59 |
| Lactiplantibacillus carotarum | GCF_947539765.1 | 80.33 | 0.98 |
| Vagococcus jeotgali | GCF_035918315.1 | 94.2 | None |

## Held-back closed-assembly species

- Pediococcus damnosus: affirmative_isolate_or_culture_source_support_missing
- Enterococcus gilvus: affirmative_isolate_or_culture_source_support_missing
- Pediococcus cellicola: affirmative_isolate_or_culture_source_support_missing; ncbi_atypical
- Pediococcus ethanolidurans: affirmative_isolate_or_culture_source_support_missing
- Enterococcus devriesei: affirmative_isolate_or_culture_source_support_missing
- Pediococcus argentinicus: affirmative_isolate_or_culture_source_support_missing
- Streptococcus danieliae: affirmative_isolate_or_culture_source_support_missing
- Oenococcus alcoholitolerans: affirmative_isolate_or_culture_source_support_missing

Existing provisional panels and acquisition batches are preserved byte-for-byte. This review creates only an ancillary immutable queue, audit and document; it launches no acquisition or scientific computation.
