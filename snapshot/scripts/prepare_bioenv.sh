#!/usr/bin/env bash
set -euo pipefail
ROOT='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
mkdir -p "$ROOT/tools/conda_pkgs" "$ROOT/work/conda_tmp" "$ROOT/evidence/tooling"
export CONDA_PKGS_DIRS="$ROOT/tools/conda_pkgs"
export CONDA_ENVS_PATH="$ROOT/tools/envs"
export TMPDIR="$ROOT/work/conda_tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export XDG_CACHE_HOME="$ROOT/work/xdg_cache"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
printf '=== resource admission ===\n'
date -u --iso-8601=seconds
hostname
free -b
df -B1 "$ROOT"
printf '=== mount ===\n'
findmnt -T "$ROOT" -o SOURCE,TARGET,FSTYPE,OPTIONS
printf '=== conda version ===\n'
/root/miniconda3/bin/conda --version
printf '=== admission check ===\n'
python3 - "$ROOT" <<'PY'
import pathlib, shutil, sys
available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
free=shutil.disk_usage(sys.argv[1]).free
print({'mem_available_bytes':available,'disk_free_bytes':free})
assert available>=2*1024**3, 'Solver not admitted: need >=2 GiB available, preserve >=1 GiB headroom'
assert free>=25*1024**3, 'Need >=25 GiB disk free'
PY
/root/miniconda3/bin/conda create --dry-run --json --solver libmamba --override-channels --no-default-packages --copy -p "$ROOT/tools/bioenv" -c https://conda.anaconda.org/conda-forge -c https://conda.anaconda.org/bioconda prodigal hmmer mmseqs2 skani > "$ROOT/evidence/tooling/conda_dryrun.json" 2> "$ROOT/evidence/tooling/conda_dryrun.stderr"