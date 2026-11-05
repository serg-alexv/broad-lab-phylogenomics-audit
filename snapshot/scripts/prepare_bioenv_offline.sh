#!/usr/bin/env bash
set -euo pipefail
ROOT='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
export CONDA_PKGS_DIRS="$ROOT/tools/conda_pkgs" CONDA_ENVS_PATH="$ROOT/tools/envs"
export TMPDIR="$ROOT/work/conda_tmp" TMP="$ROOT/work/conda_tmp" TEMP="$ROOT/work/conda_tmp"
export XDG_CACHE_HOME="$ROOT/work/xdg_cache"
export CONDA_REGISTER_ENVS=false CONDA_REPORT_ERRORS=false CONDA_NOTIFY_OUTDATED_CONDA=false CONDA_AUTO_UPDATE_CONDA=false
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
python3 - <<'PY'
from pathlib import Path
available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
print({'mem_available_bytes':available})
assert available>=2*1024**3, 'Need >=2GiB before solver'
PY
/root/miniconda3/bin/conda create --dry-run --json --solver libmamba --override-channels --no-default-packages --copy --repodata-fn repodata.json -p "$ROOT/tools/bioenv" -c "file://$ROOT/work/conda_channels/conda-forge" -c "file://$ROOT/work/conda_channels/bioconda" prodigal hmmer=3.4=h503566f_3 mmseqs2 skani > "$ROOT/evidence/tooling/conda_offline_dryrun.json" 2> "$ROOT/evidence/tooling/conda_offline_dryrun.stderr"