# Phylogeny stage order and matrix QC - 29 October 2026

The automatic handoff moved from completed gene diagnostics to defence prediction before resolving the selected phylogeny matrix. That priority was wrong. Stage07 also used a default NOT_STARTED label that hid completed candidate alignments; Stage08 displayed an old ten-taxon exploratory result. The visible monitor and continuation policy now distinguish these states and prioritize06 ->07 ->08 ->09.

## Actual completed work

- 196 candidate-family alignments and196 diagnostic gene trees across919 genomes are accepted and closed. The gene diagnostics consumed26,666.54 scientific seconds (about7.4hours); their recorded Linux RSS plus private-RAM peak was851,542,016bytes. They did not fail from memory.
- A conservative54-marker computational core holds three alignment-sensitive loci and excludes multicopy/nonuniversal candidates. It does not prove absence of hidden paralogy.
- Nineteen genomes are held from the primary computational cohort:4 exceed0.5% DNAambiguity,13 have inconclusive sourceANI, and2 have cross-method QC disagreements. None is silently called a biological failure or resolved negative. The remaining900 represent684 source species labels; final eligible-species/taxonomic acceptance is unresolved.
- The900 x54 matrix contains13,071 AAcolumns,10,784 variable and10,431 parsimony-informative columns. Maximum taxon missingness is1.599%. Nine descriptive composition outliers are retained for model/taxonomic review.
- Construction resumed from a deliberately closed seven-locus checkpoint; all seven commits and artefacts stayed byte-identical. Resume exited0 in7.766seconds and recorded100,409,344bytes Windows OSpeak RSS internally. External exit-receipt RSS is unavailable, not invented.
- An independent implementation reconstructed every source mask, residue, coordinate, partition and output byte; computational QC passed. This does not grant final orthology, taxonomy or tree acceptance.

## Next execution

The existing finite five-genome defence pilot is already running. Its source cannot yield between units safely; it will close normally, with no additional defence bulk before the primary phylogeny path. The local event controller will then prioritize a separately admitted Stage08 model/resource pilot on this exact matrix, followed by full inference and independent validation as gates permit. No human input or reminder is required. Final biological review and expanded-seed robustness remain required before final deliverable acceptance.

## Evidence

Root acceptance: metadata/stage07_conservative900_54_v001/Root_ACCEPTED_COMPUTATIONAL_MATRIX.json
Independent validation: metadata/stage07_conservative900_54_v001/independent_validation.json
Matrix: analysis/phylogeny/full900_conservative54_v001/supermatrix.faa
Partitions: analysis/phylogeny/full900_conservative54_v001/partitions.nex
Held genomes: metadata/panel_critical_path_review_20261029/held19_manifest_v001.json
Marker decisions: metadata/marker_critical_path_review_20261029/all281_decisions.tsv
Monitor deployment: metadata/phylogeny_priority_monitor_20261029/V47_DEPLOYED_VERIFIED.json

The monitor refreshes every30seconds. It shows the primary stage order separately from actual background activity, and hides stale CheckM2 counters during the current defence pilot. All work remains local; no project material was uploaded.
