# CheckM1 taxonomic runtime

Runtime ready; no genomic QC was executed by setup. The actual import/CLI smoke completed in 74.867856 seconds with all four original CLI help calls and the enclosing WSL command returning zero. `metadata/checkm1_taxon_setup_v001/runtime_READY.json` binds the binaries, software/data manifests, source receipts and exact environment.

## Runnable route

The Python interpreter is `tools/checkm1_env/bin/python` (3.11.18). The unchanged CheckM1 1.2.5 entry is `tools/qc_fallback_staged/checkm1_1_2_5_unpacked/python-scripts/checkm`.

For Linux project root `$R`:

```bash
export PYTHONPATH="$R/tools/checkm1_wheel_overlay311/site-packages:$R/tools/qc_fallback_staged/checkm1_1_2_5_unpacked/site-packages"
export CHECKM_DATA_PATH="$R/tools/databases/checkm1_2015_01_16/reference"
export PATH="$R/tools/bioenv/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 MPLBACKEND=Agg
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
```

The execution owner supplies project-owned scratch, XDG and Matplotlib cache directories and the reviewed private short IPC alias/prewarm. Scientific commands, output paths, resource limits and admission belong to the Root pilot controller. The stock command sequence is:

```bash
"$R/tools/checkm1_env/bin/python" -B "$R/tools/qc_fallback_staged/checkm1_1_2_5_unpacked/python-scripts/checkm" taxon_set order Lactobacillales ORDER.ms
"$R/tools/checkm1_env/bin/python" -B "$R/tools/qc_fallback_staged/checkm1_1_2_5_unpacked/python-scripts/checkm" analyze -g -x faa -t 4 --tmpdir PROJECT_SCRATCH ORDER.ms ORIGINAL_PRODIGAL_FAA_DIRECTORY OUTPUT_DIRECTORY
"$R/tools/checkm1_env/bin/python" -B "$R/tools/qc_fallback_staged/checkm1_1_2_5_unpacked/python-scripts/checkm" qa -t 4 -o 1 --tab_table -f REPORT.tsv --tmpdir PROJECT_SCRATCH ORDER.ms OUTPUT_DIRECTORY
```

These commands do not perform placement, DIAMOND search or new gene calling. This is a minimal runtime for the selected taxonomic protein route; coverage and placement dependencies/workflows were not installed or validated.

## Software and original material

The official Bioconda package `checkm-genome-1.2.5-pyhdfd78af_1.conda` is preserved, SHA256 `6f8b2a89eff778e2906b6db9260e1031b1d4b3732cfd69c1ced57e8fd4c253dc`. Its 85 original extracted files, including notices and package metadata, are unchanged. Software license is GPL-3.0-or-later.

The original 2015-01-16 reference archive is preserved, SHA256 `971ec469348bd6c3d9eb96142f567f12443310fa06c1892643940f35f86ac92c`; its author MD5 matches. Its 33 extracted files total 1,495,861,394 bytes. The [author's Zenodo record](https://zenodo.org/records/7401545) does not supply a separate data-license label in the inspected metadata; no label is invented here. The original [CheckM paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4484387/) describes the estimator.

Twenty-six exact official Conda archives supplied Python 3.11 and its base dependencies. The first copy-mode transaction did not complete at its 600-second command boundary and remains unaccepted at `tools/checkm1_env_partial_v003_600s`; its logs and observed nonzero tool exit are preserved, while the original inner Conda exit was not captured. The same verified cache was then linked into a fresh prefix, with actual transaction exit zero and 26 package records. No new solve, download or package version was introduced by recovery.

Fifteen official, hash-locked CPython 3.11 wheels were extracted using Windows filesystem access into `tools/checkm1_wheel_overlay311/site-packages`. All source SHA256 and wheel RECORD checks passed; all 4,729 extracted files / 263,992,614 bytes were read back exactly. Licenses, distribution metadata and native `.libs` directories remain intact. Four non-import wheel data files are retained separately. This is an extracted overlay, not a pip installation.

Actual imports bind NumPy 1.26.4, SciPy 1.13.1, Matplotlib 3.9.4, DendroPy 4.6.1 and setuptools 75.8.2 to that overlay. The Conda base setuptools 84.2.1 record remains preserved and is explicitly shadowed by the selected 75.8.2 overlay. HMMER 3.4 / Easel 0.49 come from the existing project bioenv; `hmmsearch`, `hmmfetch` and `hmmalign` help/version calls each returned zero. Their original package/license provenance is retained in the project.

## Scientific input and marker contract

Use original accepted Prodigal FAA files, retaining scaffold/gene-number IDs and original coordinate/partial headers. The canonical protein IDs discard the syntax used by stock adjacent-ORF and pseudogene corrections. Those corrections remain enabled; no coordinates, return values or annotation successes are synthesized.

The original order row has 337 markers, 184 sets and 490 reference genomes. Stock CheckM1 excludes TIGR00398/TIGR00399 and removes the resulting empty set, yielding 335 markers / 183 sets for the selected order estimate. `taxon_set` also emits ancestors; their extraction union contains 367 distinct HMMs. These are different counts with different meanings, not a modified marker scheme.

Protein mode does not provide valid nucleotide GC/genome-size/coding-density measurements. Use QA format 1 for completeness/contamination and retain independently measured DNA metrics separately. Original source/taxonomy/unknown masks and prior failures survive. The order-reference estimate is a different method from CheckM2 and is not numerical truth or panel acceptance.

Stock worker exceptions can leave an apparently successful parent command, so the pilot must validate all expected input names, nonempty HMM outputs, marker/schema counts and finite per-bin results in addition to actual process exits. The setup smoke searched no genome and proves no numerical QC result.
