# Completeness/contamination QC readiness

Checked 2026-10-26. This document records readiness and a bounded execution route. It is not a CheckM2 result. No independent completeness/contamination prediction has run in this project.

## Current state

The official CheckM2 database is downloading through the Windows worker `scripts/download_checkm2_db.py`. `state/completeness_db_progress.json` is the live byte journal; `state/launch_completeness_db.json` records the actual PID and creation time. Closing the progress console does not stop this worker. `state/STOP` requests a controlled stop. Partial bytes stay under `work/models/checkm2_v3/`; verified archives are committed under `tools/databases/checkm2_v3/`.

The separate CheckM2 Python/TensorFlow environment is **NOT INSTALLED**. Its resource pilot is **NOT RUN**. A finished archive download alone must not change either state to ready or passed.

## Primary route: CheckM2 1.1.0 and the matched v3 database

| Component | Verified pin/source |
|---|---|
| Program package | `checkm2-1.1.0-pyhdfd78af_2.conda`, official Bioconda noarch channel, 47,250,052 bytes |
| Package SHA256 | `1af64d8c354104818d0b7d4fbc23c7c875e8a8b73f2541ecf1d39b90385f27d2` |
| Runtime to resolve | Python3.12, TensorFlow>=2.17,<2.20, scikit-learn>=1.6.1, Keras, LightGBM, NumPy, pandas, SciPy, requests, packaging, tqdm, Prodigal>=2.6.3; exact builds remain to be solved and verified |
| DIAMOND | Pin2.1.11, the version explicitly named by the dataset creator; do not silently select current2.2.x |
| Database | Creator Alex Chklovski, CM2 Reference Database Uniref100/KO v3, published2025-02-20, DOI10.5281/zenodo.14897628 |
| Database bytes | 1,735,095,710 compressed |
| Published MD5 | `07c10655620843b517d0df0c160d911f` |
| Direct source | `https://zenodo.org/api/records/14897628/files/checkm2_database.tar.gz/content` |

The database version/compatibility and published file checksum are provided by the [creator's Zenodo record](https://zenodo.org/records/14897628). A local copy of its API metadata is retained in `evidence/completeness_qc/zenodo_cm2_v3.json`.

The [Bioconda program archive](https://conda.anaconda.org/bioconda/noarch/checkm2-1.1.0-pyhdfd78af_2.conda) was downloaded, channel-SHA256 checked and inspected. It contains the pretrained Keras, LightGBM and scaler models; those models are not an additional GitHub download. The package's full unpacked payload is80,989,621 bytes. Inspection retains original package info, recipe and GPL3 notice under `evidence/completeness_qc/checkm2_package_inspection/`; its file inventory is adjacent. Source URLs mentioned inside package metadata were not followed.

Do not use PyPI's currently exposed old1.0.1 distribution with this v3 database: the requested pin is1.1.0, and compatibility must come from the matched package/database rather than a generic package name.

### Installation boundary

Do not invoke `conda create`, `conda env`, or other conda entrypoints against the host registry. Earlier conda registration disabling did not prevent a shared environment-list timestamp change. There is currently no verified registry-free installer in this project.

The next safe preparation step is to resolve the above exact stack from the already cached official conda-forge/Bioconda metadata and retain URLs, SHA256s, dependency closure and original notices. Actual creation must use a demonstrably project-only prefix/cache/linking path, or a tested private mount namespace that maps every possible registry/cache write into the project. Verify that isolation before installation; do not assume `CONDA_REGISTER_ENVS=false` provides it. No old environment is a suitable shortcut for TensorFlow/Python compatibility.

**Precise gate:** `ENVIRONMENT_NOT_INSTALLED_PRIVATE_INSTALLER_UNVERIFIED`. This is an implementation/isolation gate, not a finding that CheckM2 is scientifically unusable or that its database needs GitHub.

### Memory and execution admission

Inspection of the pinned `checkm2/diamond.py` establishes that `--lowmem` selects DIAMOND block size0.5 instead of2, with default annotation chunks of250 genomes. This is a memory-reduction option, not a2GiB maximum-RAM guarantee. TensorFlow/Keras are imported by the prediction stack. Their combined process-group memory with DIAMOND has not been measured here.

After the environment and archive are verified:

1. Extract the database through safe-member checks into the project; retain the original archive and creator metadata. Match the package's expected database checksum/version. Use explicit `--database_path`; do not run a database setter that edits an internal/global location.
2. Smoke-test all component versions, model/scaler loading and the program's own test genomes in a project-owned output/temp directory.
3. Admit one source-supported genome only:2 threads, `--lowmem`, project-only TMP/XDG/cache paths, >=1GiB Linux headroom, >=40GiB disk reserve, <=2GiB sampled process-group RSS and a finite10-minute pilot deadline. Keep HOME and global WSL configuration unchanged.
4. Stop and preserve outputs if the budget fails. Do not increase RAM, alter DIAMOND internals, change its block size below the program's supported setting, or replace the method silently. A passing pilot permits a ten-genome batch; a passing measured batch permits deterministic small resumable batches, not an unmeasured1,000-genome launch.
5. Preserve Prodigal/DIAMOND outputs only with matching input, executable, database and option hashes before `--resume`. Publish per-genome prediction values and warnings. Missing, interrupted or failed predictions remain unresolved.

The project95% completeness/5% contamination gates remain in force after independent predictions. Reduced-genome or lineage-estimator disagreement requires documented review rather than automatic promotion or biological-absence claims.

## One bounded corroboration fallback: fixed-lineage BUSCO

If the primary CheckM2 route cannot pass the current isolation/resource gate, BUSCO can provide a separately labelled completeness/duplication cross-check. It is **not a substitute contamination estimate** and cannot by itself admit genomes through the full95%/5% quality gate.

The [official BUSCO6.1.0 guide](https://busco.ezlab.org/busco_userguide.html) documents prokaryotic Prodigal/HMMER operation, fixed-lineage offline execution, restart behavior, and Complete/Single-copy/Duplicated/Fragmented/Missing outcomes. Use `--offline`, an explicit lineage, project-owned download/output paths and `--opt-out-run-stats`; do not enable automatic lineage downloads or telemetry.

The official dataset inventory currently pins `lactobacillales_odb12.2`, date2026-05-22, MD5`0ad3a87ae3fee384760549796a7b9f65`. Its narrower lineage is appropriate only after taxonomy is confirmed; it remains an independent QC reference, not a replacement for de novo phylogenetic marker discovery. Contamination remains UNKNOWN if no supported independent method has run.

The official inventory URL `https://busco-data.ezlab.org/v5/data/file_versions.tsv` explicitly redirects to `https://busco-data.s3.amazonaws.com/file_versions.tsv`; that exact non-GitHub target was manually checked and returnedHTTP200. The inventory and redirect chain/checksums are retained in `evidence/completeness_qc/`. No BUSCO lineage archive or environment was installed by this audit.

## Evidence and restrictions

No GitHub endpoint was opened, cloned or downloaded by this preparation; downloaded program payloads came only from the official Bioconda channel. No genomic inputs were uploaded. No conda entrypoint, global WSL setting, Docker service, old analysis or old environment payload was modified. The initial large combined shell launcher was rejected before dispatch; separating the file edit from the short launcher succeeded under the existing authorization. The active database worker is the successful bounded action, not an approval workaround.
