#!/bin/bash
#
# Scripts/record_demo.sh — Phase 20: record a sub-90s demo
#
# Skips rebuild and uses FAST mode. Requires asciinema (optional).
#
# Usage:
#   ./Scripts/record_demo.sh            # run timed demo only
#   RECORD=1 ./Scripts/record_demo.sh   # also save demo.cast via asciinema

set -euo pipefail

cd "$(dirname "$0")/.."

if [ "${RECORD:-0}" = "1" ]; then
    if ! command -v asciinema >/dev/null 2>&1; then
        echo "ERROR: asciinema not installed. Install with: pip install asciinema"
        exit 1
    fi
    echo "Recording demo to demo.cast (target: under 90 seconds)..."
    FAST=1 asciinema rec --overwrite demo.cast --command "bash Scripts/run_demo.sh"
else
    echo "Running fast demo (no recording)..."
    FAST=1 bash Scripts/run_demo.sh
fi

if [ -f demo.cast ]; then
    echo "Recording saved: demo.cast"
fi
