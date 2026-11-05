#!/bin/bash
set -euo pipefail
ROOT='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
[[ "${TREE2_PRIVATE_NAMESPACE_VERIFIED:-}" == 1 ]] || exit 4
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
exec /usr/bin/python3 -B "$ROOT/scripts/checkm2_ipc_proof_inside.py"
