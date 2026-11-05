#!/bin/bash
set -euo pipefail
ROOT=/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026
PREFIX="$1"
REQUEST="$2"
REQUEST_SHA="$3"
OUTPUT="$4"
set +e
"$PREFIX/bin/python" -B "$ROOT/scripts/checkm2_P20_diamond_exec_producer_v001.py" --request "$REQUEST" --request-sha256 "$REQUEST_SHA" --output "$OUTPUT"
search_exit=$?
set -e
if [[ "$search_exit" -ne 0 ]]; then exit "$search_exit"; fi
exec "$PREFIX/bin/python" -B "$ROOT/scripts/checkm2_P20_diamond_exec_validate_v001.py" --request "$REQUEST" --request-sha256 "$REQUEST_SHA" --output "$OUTPUT" --observed-search-exit-code "$search_exit"
