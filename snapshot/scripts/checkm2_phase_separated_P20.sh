#!/bin/bash
set -euo pipefail
ROOT='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
[[ "${TREE2_PRIVATE_NAMESPACE_VERIFIED:-}" == 1 ]] || { echo 'Private namespace is required' >&2; exit 4; }
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONWARNINGS=default
export TMPDIR="$ROOT/work/checkm2_private_tmp" TMP="$ROOT/work/checkm2_private_tmp" TEMP="$ROOT/work/checkm2_private_tmp"
export XDG_CACHE_HOME="$ROOT/work/checkm2_private_xdg" XDG_CONFIG_HOME="$ROOT/work/checkm2_private_config"
export KERAS_HOME="$ROOT/work/checkm2_keras" MPLCONFIGDIR="$ROOT/work/checkm2_mpl" NUMBA_CACHE_DIR="$ROOT/work/checkm2_numba"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 CUDA_VISIBLE_DEVICES=-1
exec /usr/bin/python3 -B "$ROOT/scripts/checkm2_phase_separated_entry_P20.py"
