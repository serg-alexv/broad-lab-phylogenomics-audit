# Source-only review of ANI flags

The existing170 ANI flags were reviewed using their287 genomes' cached NCBI assembly/BioSample reports,current taxonomy metadata and recorded source holds. Every source report matched the byte count and SHA256 in its acquisition receipt. No ANI calculation,genome pruning,species renaming or taxonomy acceptance was performed.

Review-only evidence is committed under analysis/sequence_qc/d64e016face251f1/curation_source_review/3fa9c62b41bb4a54/. It contains source_evidence.json,pair_reviews.json/.tsv,component_reviews.json/.tsv,strict_near_duplicate_components.json,summary.json,manifest.json andcommit.json. Inputs bind the existing ANI commit/table,the original DNA input manifest,the source audit,taxonomy map and curation script hashes. The287 original source records themselves remain untouched.

## Type-material distinctions

Within the full824-genome screen,NCBI source labels were673 TYPE_MATERIAL,143 with no explicit label,5 TYPE_MATERIAL_SYN and3 TYPE_MATERIAL_NEOTYPE. The287 flagged genomes include254 TYPE_MATERIAL,31 unlabelled and2 neotypes. No clade/reference-proxy category appears in this screen.

An arbitrary nonempty type-material object is not a nomenclatural anchor. The earlier screen's anchor flag required EXACT TYPE_MATERIAL,not the boolean field. This review retains TYPE_MATERIAL as a SOURCE assertion with unverified taxon scope; assembly type objects do not independently establish a species-level nomenclatural relationship. Neotypes and synonym types require their own nomenclature/name curation. Clade exemplars,co-identical/reference proxies,pathovar types and unknown labels would remain distinct and would not automatically become species-type anchors. Zero independently verified nomenclatural anchors means verification was not performed; it does not mean these genomes lack real type status.

## Identity evidence and priorities

The170 flagged pairs form134 connected review components. Forty-two cross-label pairs form14 priority1 components requiring species-name/type-reference review. Twelve priority2 components cover shared-source-identity redundancy or the within-label borderline case;108 priority3 components are strain-diversity/shared-DNA review. Component membership does not imply every member pair directly meets a threshold.

There are zero shared BioSample pairs,two pairs with a shared normalized strain value and12 with a shared normalized culture-collection token (overlapping evidence categories). Culture token normalization is a matching aid,not proof of a shared physical stock. Shared culture/type metadata can identify likely re-sequencing of the same deposited strain despite different BioSamples,but no records were collapsed.

The119 stricter near-duplicate pairs (ANI>=99.99%,AF>=95% BOTH directions) remain119 two-genome review components. High ANI does not establish identical plasmid/accessory/defence content,so no pruning or representative replacement is implied.

The within-label Streptococcus sanguinis comparison,GCF_013343115.1 versus GCF_900475505.1,has skani ANI94.87% and AF83.82%/86.08%. Its reported5th/95th ANI percentiles are94.58/95.13,which straddle the95% review threshold. The first genome's cached NCBI ANI metadata names the GenBank partner GCA_900475505.1 as its type reference,records ANI95.14% and taxonomyCheckStatus=OK. The second genome has a TYPE_MATERIAL assertion; the first has no explicit type-material claim. This is a method/threshold-sensitive review case,not evidence sufficient for a mislabel call. Different estimators are not interchangeable,even when the reference pair is the same.

None of these287 genomes has a recorded source hold in the audited source snapshot. This is expected because the ANI cohort excluded held/MAG/SAG inputs; it is not a new biological-QC pass. Completeness/contamination,independent sequence taxonomy and final species/strain selection still require their own gates. Missing metadata remains unknown. All decisions here are REVIEW_ONLY.
