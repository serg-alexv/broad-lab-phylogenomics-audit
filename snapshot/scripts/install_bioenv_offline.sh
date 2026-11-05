#!/usr/bin/env bash
set -euo pipefail
ROOT='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
export CONDA_PKGS_DIRS="$ROOT/tools/conda_pkgs" CONDA_ENVS_PATH="$ROOT/tools/envs"
export TMPDIR="$ROOT/work/conda_tmp" TMP="$ROOT/work/conda_tmp" TEMP="$ROOT/work/conda_tmp"
export XDG_CACHE_HOME="$ROOT/work/xdg_cache"
export CONDA_REGISTER_ENVS=false CONDA_REPORT_ERRORS=false CONDA_NOTIFY_OUTDATED_CONDA=false CONDA_AUTO_UPDATE_CONDA=false
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
python3 - "$ROOT" <<'PY'
import json,pathlib,shutil,sys
r=pathlib.Path(sys.argv[1])
admission=json.loads((r/'evidence/tooling/package_size_and_notices.json').read_text())
assert admission['admitted_under_2GiB']
available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert available>=2*1024**3
assert shutil.disk_usage(r).free>=25*1024**3
resolved=json.loads((r/'evidence/tooling/resolved_packages.json').read_text())
text='@EXPLICIT\n'+'\n'.join(x['url']+'#'+x['md5'] for x in resolved)+'\n'
(r/'evidence/tooling/bioenv_explicit_local.txt').write_text(text)
print({'available_bytes':available,'conservative_footprint_bytes':admission['conservative_total_footprint_bytes']})
PY
/root/miniconda3/bin/conda create --offline --json --no-default-packages --copy -y -p "$ROOT/tools/bioenv" --file "$ROOT/evidence/tooling/bioenv_explicit_local.txt" > "$ROOT/evidence/tooling/conda_install.json" 2> "$ROOT/evidence/tooling/conda_install.stderr"
printf '\n=== installed binaries smoke checks ===\n'
"$ROOT/tools/bioenv/bin/prodigal" -v 2>&1
"$ROOT/tools/bioenv/bin/hmmsearch" -h | head -12
"$ROOT/tools/bioenv/bin/mmseqs" version
"$ROOT/tools/bioenv/bin/skani" --version
printf '\n=== resource receipt ===\n'
free -b
df -B1 "$ROOT"
/root/miniconda3/bin/conda list -p "$ROOT/tools/bioenv" --explicit > "$ROOT/evidence/tooling/bioenv_explicit_export_local.txt"
/root/miniconda3/bin/conda list -p "$ROOT/tools/bioenv" --json > "$ROOT/evidence/tooling/bioenv_installed_packages.json"