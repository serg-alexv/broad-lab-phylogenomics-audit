# Defence model acquisition audit

Audit date: 2026-10-26. No prediction was run and no defence program was installed by this audit. Project data stayed local. Only official Bioconda package downloads and non-GitHub official documentation/papers were accessed; updater commands were inspected as text and were not executed.

## Confirmed package route

Official package archives can be acquired from `conda.anaconda.org` without GitHub. The following archives were downloaded into `evidence/model_routes/`, verified against the project's saved official Bioconda repodata SHA256, and listed without installation:

| Package | Bytes | SHA256 |
|---|---:|---|
| `padloc-2.0.0-hdfd78af_1.conda` | 2,717,093 | `cc0c1f7453e58a3485104fd0336c24730f036b3e36af33bd73fcb45fd1b94d9d` |
| `defense-finder-3.0.0-pyhdfd78af_0.conda` | 74,147 | `c13a1e3c7dec4e3451ab128516a0b65f0351e15ecfd046a665038cbd57cb5ba7` |

Sources: [PADLOC official package listing](https://anaconda.org/channels/bioconda/packages/padloc/files), [Bioconda noarch repository](https://conda.anaconda.org/bioconda/noarch/).

Neither archive contains the required defence HMMs or complete-system models. The PADLOC payload has 16 paths: wrapper/R code, auxiliary installers, test data and notices. DefenseFinder has 36 paths: Python code, metadata and optional exploratory model configuration/tokenizer files; its one YAML is a GeneCLR configuration, not a complete-system definition.

Machine-readable package hashes, dependencies and model-file counts are in `evidence/model_routes/package_model_inventory.json`; full payload paths are in the accompanying `.files.txt` files. Compressed payloads are also retained for independent inspection. These archive inspections do not establish a working project environment.

## Model source blocker

PADLOC's inspected updater explicitly points at the upstream GitHub PADLOC-DB repository. DefenseFinder's inspected updater delegates `defense-finder-models` and `CasFinder==3.1.0` to `macsydata`. The official current package documentation describes model retrieval separately from program installation. Do not run these automatic update operations under the present no-GitHub boundary.

The [official PADLOC webserver](https://padloc.otago.ac.nz/padloc/) identifies PADLOC-DB 2.0.0 and links its model source to GitHub; its precomputed result downloads are predictions, not a complete local model distribution. The [official DefenseFinder documentation](https://pypi.org/project/mdmparis-defense-finder/) likewise treats models as a separate installation.

The author-deposited [Zenodo record 13762622](https://zenodo.org/records/13762622) is titled *Code for the DefenseFinder Wiki*. It is a website/wiki source snapshot, not a validated full model archive, and cannot substitute for the prediction models. A third-party 12.7GB functional-annotation bundle lists DefenseFinder material, but it is not an independently established official complete model release and was not downloaded or substituted. Individual paper supplements with a narrow system's models likewise cannot replace the broad defence catalogue.

**Result:** no verified official non-GitHub route for the complete required model catalogues was found in this bounded audit. Model acquisition is `BLOCKED_NO_VERIFIED_NON_GITHUB_SOURCE`. This is a statement about verified routes, not proof that no archive exists anywhere. Continue genome QC/annotation/marker work while preserving the blocker. A future complete archive must have its official provenance, version, compatibility, notices, checksums, required files and positive-control behaviour verified before prediction is admitted. Do not silently use precomputed web predictions or upload genomes to a web service.

## Additional scientific filter

The PADLOC server states that DB 2.0.0 includes candidate systems inferred by a guilt-by-embedding approach. Before ring generation, record a model-level evidence catalogue. Exploratory candidate classes must not be presented as experimentally established antiphage systems, and partial/relaxed calls must not be promoted to complete-system positives. “Complete predicted system” remains model-relative even for established classes.

## 2026-10-27 permitted-source recheck: legacy candidate preserved

A further package-metadata search found the author-named Anaconda channels [padlocbio](https://api.anaconda.org/package/padlocbio/padloc) and [leightonpayne](https://api.anaconda.org/package/leightonpayne/padloc). The `padlocbio` 2.0.0 archive passed its published SHA256/MD5 but contains no HMM library. The older `leightonpayne` 1.0.0 archive contains a database in its build-recipe inputs: release text `VERSION: 1.0.0`, 36 system YAML files and one 194,719,083-byte concatenated HMM library. Its published MD5 matches; local archive SHA256 is `79059e1a70ac617762a75b0ea5617c5d6e61af34252b43d959475b823e837a66`.

This is a **held legacy candidate**, not an accepted replacement for the required broad catalogues. Channel ownership is not independently authenticated; database compatibility, profile/definition integrity, catalogue completeness and positive controls have not passed. The 36 legacy system filenames do not include RM or Cas definitions. DefenseFinder's complete models still have no verified permitted source. Five small original database release/readme/license/metadata files were preserved byte-for-byte; the model library was not extracted, installed or executed. No genome was submitted, no GitHub host was accessed, and defence states remain NOT_RUN/unknown.

Receipts and original archives: `evidence/model_routes/author_channel_metadata_20261027/` and `evidence/model_routes/author_archive_inspection_20261027/legacy_candidate_hold.json`. The earlier failed API query is preserved separately; the corrected query used the API's required `name` parameter. This new candidate narrows the source inventory but does not clear the broad-model gate.

## 2026-10-29 current official catalogues acquired and verified

The human granted a narrow exception for read-only official MODEL downloads fromGitHub. Complete PADLOC-DB2.0.0, DefenseFinder models3.1.0 andCasFinder3.1.0 are now locally staged, version/commit/checksum-pinned and statically verified with original notices. The GitLabteaching snapshots were incomplete and remain held. Stock runtimes, native model loading and positive/incomplete/contig functional controls passed; full results and precise control scopes are in docs/DEFENCE_PREPARATION_20261029.md and metadata/defence_parallel_preparation_20261029/STAGE_PREPARATION_READY.json. Earlier modelsource blocks above are historical and superseded by this exception/acquisition.

The ready scope is protein-supported prediction with explicit availability masks.51PADLOCmodels requireCRISPR/ncRNA feature inputs; unavailable states remainUNKNOWN,nevernegative. Source/RNA predictor limitations and exactnextsteps are preserved, rather than silently reannotating or broadening the GitHub exception. No projectgenomes, sourcefiles orresults were uploaded. No production defence call has yet been made.
