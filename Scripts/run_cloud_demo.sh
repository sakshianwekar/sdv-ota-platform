#!/bin/bash
#
# Scripts/run_cloud_demo.sh — End-to-end demo via FastAPI server + OTA client
#
set -euo pipefail

cd "$(dirname "$0")/.."
CLOUD=1 FAST="${FAST:-1}" bash Scripts/run_demo.sh
