#!/bin/bash
# Cross-platform wrapper — delegates to Python demo (macOS/Linux).
set -euo pipefail
cd "$(dirname "$0")/.."
ARGS=()
[ "${FAST:-0}" = "1" ] && ARGS+=(--fast)
[ "${CLOUD:-0}" = "1" ] && ARGS+=(--cloud)
exec python3 Scripts/run_demo.py "${ARGS[@]}"
