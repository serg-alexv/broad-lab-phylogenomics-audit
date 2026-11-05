# Cohort and defence status tables

- `acquired_genomes.tsv` lists the 1,170 exact versioned assemblies with source labels, integrity measurements, source disposition, CheckM1 estimates where evaluated, diagnostic CheckM2 estimates where available, and membership in the 919-genome defence queue and 900-tip computational tree.
- `defence_status.tsv` lists all 919 frozen targets. A per-detector accepted count comes from a closed cohort with independent QA. C009 has a separate computed-pending-QA count and blank accepted columns. An unrun or unavailable result has a blank count and its explicit status.
- `table_manifest.json` binds the tables and their source artifacts by SHA256 and records aggregate counts. `build_status_tables.py` reproduces the export from the corresponding audit evidence tree.

The source audit predates the completed CheckM1 method estimates. Its original disposition labels are preserved beside the newer method results. Species and genus are source labels. A CheckM1 95/5 pass is a method result, while independent taxonomy and final panel acceptance remain open.

The detector columns separate all stock calls, complete model-relative predicted systems, and the primary complete-protein subset after documented exclusions. A verified zero is limited to the detector's assessed model scope. A zero in the primary subset can coexist with other stock calls. RNA-dependent PADLOC models, unavailable Cas array evidence and out-of-scope or unsearched models remain unknown. Neither dataset makes final ring or biological absence calls.
