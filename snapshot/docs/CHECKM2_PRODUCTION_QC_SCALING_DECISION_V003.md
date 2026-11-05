# V003: held production-QC scaling decision

The primary candidate separates the unchanged original DIAMOND search from resident ML. First test it on **one new, never-predicted genome**, with fresh original annotation, then stock `--genes --resume` and full feature validation. Do not rerun the ten existing method rows. A later five-genome cohort could amortize database/model initialization, but needs its own resource qualification and admission. The bounded fallback is the now-measured stock single-FAA route for separately admitted unstarted inputs. Neither switching nor retrying is automatic.

This is a source/design decision only. S1R2 native/WSL exits and the success audit passed; Root accepted the audit after rehashing 326 files. Separate file-only compound finalization remains pending. No production, taxonomy, panel or new execution acceptance is asserted here. The earlier V001/V002 designs and failed bulk/old20 work remain preserved; their prerequisites and budgets do not govern this proposal.

## Measured basis

Only existing JSON receipts were read. Nine fresh quality calls took **1,893.535 s** in total (median 200.422 s, range 190.672–276.394 s); their nine validators took **36.628 s** (median 3.961 s, maximum 4.256 s). Combined per-row times were 194.602–280.288 s, totaling **1,930.1632848259906 s**. The retained first boundary annotation took 13.877623842003231 s; the nine new unique CONTINUE annotation receipts sum to 83.07931097700202 s. The ten unique accepted units therefore total **96.95693481900526 s**, with maximum 15.926 s and peak 166,129,664 bytes. The cumulative CONTINUE ledger already includes the first boundary; adding it again would double-count. The separate historical 600 s unknown annotation allocation is not one of these ten accepted units and remains unchanged.

The worst quality RSS was **2,090,467,328 bytes**, only **57,016,320 bytes below the unchanged 2 GiB limit**. Minimum Linux availability was 1,204,060,160 bytes, only 130,318,336 above the 1 GiB floor. Passing one FAA is therefore useful evidence, not a broad memory guarantee. Existing annotations cover FAA sizes up to 1,615,422 bytes, 3,642 CDS and only 1–3 contigs. Fragmented assemblies and larger query sets remain unqualified.

The receipts measure combined quality calls, not separate search/model costs. Splitting may reduce peak overlap but adds processes, staging and checksums. No speedup or quantitative memory saving is established. The CPU-saving hypothesis concerns a later bounded cohort sharing one database search and one stock model invocation; it is not evidence from the failed ten-query run.

## Exact handoff

The prior held 14-file author-source review was rehashed. Use the original sequential ProdigalRunner without interception or source patches, preserving selected FAA, all ten returned values and separate DNA metadata. A model-free process must enter the original `diamond` module directly: normal CLI imports predictQuality/modelProcessing and loads ML before argument handling. Actual import origins and absence of TensorFlow/Keras/LightGBM/model modules must be proved in that future phase.

Keep DIAMOND 2.1.11, database 3, original outfmt 6, threads 1, block-size 0.5, target count 1, coverage 80/80, identity 30 and e-value 1e-5. No smaller block or altered model/code/defaults is proposed. Direct DiamondRunner uses ordinary tempfile and requires at least 500 MiB free; set only its process-local tempfile directory to durable project scratch. The 32 MiB private IPC tmpfs is unsuitable. Stock resume retains accepted short-IPC prewarm, matching sklearn overlay, loader/environment controls and durable `--tmpdir`.

Every input and `resume_output/protein_files` member must be `ACCESSION.VERSION.faa`, with unchanged ordered IDs/AA/header bytes. An extensionless stock copy loses the version when resumed metadata strips its suffix. Original search prefixes primary IDs with the versioned accession and Ω. Exact input/protein/DIAMOND/feature/report name sets must match, with no sidecars or stale matching files in either trusted inventory.

Only a newly completed original-runner search with actual exit 0, creation-identified group closure and an atomic SHA/size manifest is eligible. Validate the complete twelve-field TSV, finite numeric fields, own query IDs and original target annotations; retain duplicates and a normalized full-row multiset digest. Never reuse failed T1 TSVs or infer completeness from file existence. Empty search output cannot be converted into a CheckM2 score or biological negative.

Stock resume skips annotation/search, but still initializes models, checks DIAMOND, recalculates metadata, constructs KO features and selects models. Require the unchanged explicit database; no configured-default fallback. Validate each row’s own 21,241 ordered finite/domain features, 22 FAA metadata values, 1,220 independent membership calculations, canonical `<f8` C-order digest and complete five-column report. Preserve original raw module means, clipping/denominator semantics and query-own AALength selector. This is conditional source/interface consistency, not paired numerical truth on an already measured genome. Current ten/nine validators cannot admit new names: a new independently reviewed N1/N5 binding adapter must retain the unchanged mathematics. No adapter is implemented here.

## Proposed new allocations

All allocations require new explicit authority. They neither borrow unused S1R2 time nor reset prior failures. RAM/CPU/reserve gates stay 2 CPUs, stock thread 1, 2 GiB summed owned RSS, 1 GiB headroom and 40 GiB reserve; one heavy owner runs at a time.

| Proposed scope | Annotation | Fresh model-free search | Stock resume | Full feature checks | New scientific total | Cold wall |
|---|---:|---:|---:|---:|---:|---:|
| One novel feasibility control | 180 s | 600 s | 600 s | 30 s | 1,410 s | 3,000 s |
| Later, separately qualified five-genome primary cohort | 5 × 180 s | 1,800 s | 1,500 s | 5 × 30 s | 4,350 s | 6,000 s |
| Separately admitted five-genome stock fallback | 5 × 180 s | Combined quality plus validation: 5 × 600 s shared | Included | Included | 3,900 s | 5,700 s |

Cold walls include up to 600 s initial image verification, 600 s final hash, cleanup and remaining metadata overhead. An external file-only acceptance audit would have a separate 600 s bound. Stage limits conservatively use the observed full-call maxima because isolated component costs are unknown. The five-genome limits are new allocations exceeding the old 3,600 s quota; the unchanged frozen75 observer cannot silently execute its longer stages. Future versioned operational supervision and source review are required.

After the novel control’s ordinary closure and Root method acceptance, a five-member cohort is still an unmeasured resource qualification. No transition to five, twenty, 250 or 919 is automatic. Charge every successful/failed unit’s actual time once, give each phase only its remaining stage/global allowance, and stop on the first failure. Unknown time/closure blocks. No automatic fallback, split, block reduction, replay or resource increase follows.

## Stable coverage and coordinate boundaries

The measurement universe is 919 source-supported acquired genomes. Its 95 previously unscreened records include **92 species-level labels absent from the 824 screen**; these are label/metadata counts, not authenticated species or final eligibility. Preserve the 223 separate source/review holds, 28 excluded MAG/SAG source-class records and all missing-contamination/ANI-Inconclusive reasons. Scores never clear these masks.

A future immutable queue should prioritize one acquired, technically bound accession per eligible missing label, balance family/genus, then use stable taxid/accession ties. Retain Daquilactobacillus/Hutsoniella coverage priorities. Exclude every previously predicted/claimed accession from the novel-control lane; pending accepted-row reuse decisions block replay. Only then consider extra strains. No accession is selected by this document. Out-of-envelope genomes stay queued, not biologically rejected. Extend sequence/lineage review for the 95 while preserving accepted 824/skani results and unreported-pair unknowns.

QC’s original caller deletes selected GFF/FNA; its FAA and ten returns do not establish retained gene coordinates. CheckM2 features/scores aggregate across the genome. Ω is a genome label, not a coordinate transformation. Later coordinate-complete annotation must independently bind DNA contig identities, table/program/options and ordered AA/IDs; if rerun for retained GFF, prove FAA consistency. Do not derive coordinates by splitting IDs heuristically. Fragmentation/contig-edge defence completeness remains a separate gate, and unknown defence calls remain unknown.

The accompanying HELD JSON records exact unit/source hashes, timing summaries, scope and all proposed gates. It contains no executable workflow, input selection, admission or production acceptance.
