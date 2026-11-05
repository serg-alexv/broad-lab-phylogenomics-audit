# Tree 2 source inventory

Checked 2026-10-26. These sources support design and taxonomy decisions. They do not establish that this project's scientific stages have run. Actual downloaded responses, data versions, URLs, timestamps and hashes belong in the raw-source/object manifests. Only primary papers, official service documentation and official package metadata are used here. No GitHub page was opened for this inventory and no project data was uploaded.

## Local evidence

The workspace runtime inventory records Windows host `WD`, hardware/storage and process snapshots; WSL version/config/live limits; Docker client/server checks; ordinary PATH and external read-only environment inventories. Project copies should be retained under `evidence/runtime/` and included in the manifest. Until those files are copied, the original evidence is in the session's `work/runtime_inventory*` files. Resource snapshots are time-dependent.

The retrieved NCBI OpenAPI schema is `evidence/ncbi_openapi.yaml`. Its exact URL/hash and retrieval receipt must be retained by the acquisition controller. API contents, not remembered command syntax, govern the implemented metadata retrieval.

## Taxonomy and sampling

| Source | Use and limits |
|---|---|
| [LPSN Lactobacillales](https://lpsn.dsmz.de/order/lactobacillales) | Current nomenclature/family status and synonym cross-check; not an assembly census. |
| [NCBI Lactobacillales MeSH](https://www.ncbi.nlm.nih.gov/mesh/68056546) | Broad LAB context. Use current taxonomy lineage for accession membership. |
| [NCBI Lactobacillaceae](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=33958&mode=Info) | Taxid 33958 and former Leuconostocaceae synonymy. |
| [NCBI Aerococcaceae](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=186827&mode=Info) | Taxid 186827 family anchor. |
| [NLM Carnobacteriaceae](https://meshb.nlm.nih.gov/record/ui?dcmsLinks=true&ui=D056568) | Family context; taxonomy crosswalk uses taxid 186828. |
| [NCBI Enterococcaceae](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=81852&mode=Info) | Taxid 81852 family anchor. |
| [NCBI Streptococcaceae](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=1300&mode=Info) | Taxid 1300 family anchor. |
| [Zheng et al. 2020](https://pubmed.ncbi.nlm.nih.gov/32293557/) | Primary genome-based Lactobacillus revision and family unification; motivates subtree discovery rather than an old genus list. |
| [NCBI Pseudolactococcus raffinolactis](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=1366&mode=Info) | Current accepted/submitted-name distinction and synonym example. |
| [NCBI Bifidobacterium](https://ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?command=show&id=1678&lvl=3&mode=node) | Outside the Lactobacillales ingroup; optional separate comparator only. |

## NCBI metadata, acquisition and QC

| Source | Use and limits |
|---|---|
| [NCBI Datasets assembly report schema](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/data-reports/genome-assembly/) | Assembly/annotation/sample/quality fields; missing values remain unknown. |
| [NCBI reference selection policy](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/policies-annotation/genome-processing/reference-selection/) | Type/ANI/quality selection context; reference status is not independent project QC. |
| [NCBI Datasets documentation](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/) | Official API/CLI entrypoint, with project retrieval controlled by the saved schema and receipts. |
| [NCBI GFF3 conventions](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/) | Independent acquisition verifier handles stable sequence accessions, multipart CDS/protein references and source-declared circular origin-spanning coordinates. |

The current scope is NCBI Lactobacillales taxid 186826. Raw discovery responses and taxonomy records remain the exact historical source snapshot; later service updates must not silently overwrite them. RefSeq/GenBank pairs and assembly revisions require explicit deduplication. A reference-only pilot is not the complete eligible source universe.

## Orthology, alignment and phylogenetics

| Source | Use and limits |
|---|---|
| [MMseqs2 official user guide](https://www.mmseqs.com/latest/userguide.pdf) | Sequence-search/clustering controls; clusters require separate orthology validation. |
| [Steinegger and Söding 2018: Linclust](https://pmc.ncbi.nlm.nih.gov/articles/PMC6026198/) | Fast clustering method and trade-offs; speed does not prove deep orthology. |
| [MAFFT official algorithms](https://mafft.cbrc.jp/alignment/software/algorithms/algorithms.html) | Strategy choice and speed/accuracy trade-off; final project settings require measured QC. |
| [IQ-TREE official site](https://iqtree.org/) | Current release listing; actual project binary still requires version/hash capture. |
| [IQ-TREE official tutorial](https://www.iqtree.org/doc/Tutorial) | Model selection, reduced candidate sets and support tests. |
| [IQ-TREE concordance guide](https://www.iqtree.org/doc/Concordance-Factor) | gCF and likelihood sCF as complements to bootstrap. |
| [IQ-TREE official manual](https://www.iqtree.org/doc/iqtree-doc.pdf) | Native checkpointing, resource controls and interpretation guidance. |

Resource caps, occupancy thresholds, seed-panel sizes and the staged discovery design in STAGE_PLAN.md are explicit project decisions, not claims that these sources prescribe them universally.

## Defence-system prediction

| Source | Use and limits |
|---|---|
| [Payne et al. 2021: PADLOC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8565338/) | HMM plus required-gene/synteny models; contig-break and single-gene limitations. |
| [PADLOC webserver paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9252829/) | Auxiliary RNA searches and prediction-interpretation limits; local execution is used for this project. |
| [Official PADLOC package listing](https://anaconda.org/bioconda/padloc) | Available package metadata; does not establish installed software/database readiness. |
| [DefenseFinder official PyPI description](https://pypi.org/project/mdmparis-defense-finder/) | Local installation, ordered input, separate models and output tables; pin the actual installed release and model contents. |
| [DefenseFinder official documentation](https://defensefinder.mdmlab.fr/wiki/help/defensefinder) | Distinguishes systems, genes and raw HMM-hit tables. |
| [Tesson et al. 2022: DefenseFinder](https://www.nature.com/articles/s41467-022-30269-9) | Primary model-based genomic-system detection method. |

Executable and model/database revisions are separate provenance objects. Freeze both before the first prediction; do not update models mid-panel. Complete-system outputs and model requirements determine positives; raw homology hits do not. Prediction is not experimental evidence of functional immunity. Unsupported/failed/unsearched models require availability flags. If an essential official model archive is accessible only through GitHub, record a blocked stage under the present no-GitHub boundary rather than substituting a method or fetching it silently.

See [MODEL_ACQUISITION.md](MODEL_ACQUISITION.md) and `evidence/model_routes/` for the separate bounded package/model audit. The official Bioconda program archives were acquired and hash-verified without installation; they do not bundle the required complete defence model catalogues. The inspected author-deposited [DefenseFinder Wiki Zenodo record](https://zenodo.org/records/13762622) is wiki code, not a validated model release.
