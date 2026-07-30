#!/bin/bash
#
# Scripts/run_fleet_demo.sh — Phase 17 multi-ECU fleet simulation
#
# Initializes all 3 ECUs, packages v1.1 firmware, starts OTA server,
# and runs fleet update across MotorECU + BrakeECU + BatteryECU.
#
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

SERVER_URL="${SERVER_URL:-http://localhost:8080}"
GRACE="${GRACE:-15}"
FAST="${FAST:-1}"

banner() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

ensure_keys() {
    if [ ! -f "$REPO_ROOT/Tools/keys/ota_signing_key.pem" ]; then
        python3 "$REPO_ROOT/Tools/gen_keys.py"
    fi
}

ensure_built() {
    if [ "$FAST" = "1" ]; then
        echo "FAST=1 — skipping rebuild"
        return
    fi
    banner "Building all ECU firmware + platform components"
    make -C "$REPO_ROOT/Firmware/motor_ecu" rebuild
    make -C "$REPO_ROOT/Firmware/motor_ecu_v1.1" rebuild
    make -C "$REPO_ROOT/Firmware/brake_ecu" rebuild
    make -C "$REPO_ROOT/Firmware/battery_ecu" rebuild
    make -C "$REPO_ROOT/Bootloader" rebuild
    make -C "$REPO_ROOT/Health_Monitor" rebuild
}

package_ecu() {
    local binary="$1" version="$2" ecu="$3"
    python3 "$REPO_ROOT/Scripts/package_generator.py" \
        "$binary" --version "$version" --ecu "$ecu" --out "$REPO_ROOT/packages"
}

start_server() {
    pip3 install -q -r "$REPO_ROOT/OTA_Cloud/requirements.txt" 2>/dev/null || true
    uvicorn OTA_Cloud.server:app --host 127.0.0.1 --port 8080 > /tmp/ota_fleet_server.log 2>&1 &
    SERVER_PID=$!
    sleep 2
    for _ in $(seq 1 10); do
        if curl -sf "$SERVER_URL/health" > /dev/null 2>&1; then
            echo "OTA server ready (PID $SERVER_PID)"
            return
        fi
        sleep 1
    done
    echo "ERROR: OTA server failed to start"
    cat /tmp/ota_fleet_server.log || true
    exit 1
}

stop_server() {
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}

trap stop_server EXIT

SECONDS=0
banner "SDV OTA Platform — Fleet Demo (Phase 17)"

ensure_keys
ensure_built

banner "Step 1: Initialize all virtual ECUs"
bash "$REPO_ROOT/Scripts/init_ecu.sh" all

banner "Step 2: Package v1.1 firmware for all ECUs"
mkdir -p "$REPO_ROOT/packages"
package_ecu "$REPO_ROOT/Firmware/motor_ecu_v1.1/build/motor_ecu" 1.1 MotorECU
package_ecu "$REPO_ROOT/Firmware/brake_ecu/build/brake_ecu" 1.1 BrakeECU
package_ecu "$REPO_ROOT/Firmware/battery_ecu/build/battery_ecu" 1.1 BatteryECU

banner "Step 3: Start OTA cloud server"
start_server

banner "Step 4: Fleet update — all ECUs to v1.1"
python3 "$REPO_ROOT/OTA_Client/fleet.py" \
    --server "$SERVER_URL" \
    --ecus MotorECU,BrakeECU,BatteryECU \
    --version 1.1 \
    --activate \
    --grace-duration "$GRACE"

banner "Step 5: Final ECU status"
"$REPO_ROOT/Bootloader/build/bootloader" --ecu MotorECU status
"$REPO_ROOT/Bootloader/build/bootloader" --ecu BrakeECU status
"$REPO_ROOT/Bootloader/build/bootloader" --ecu BatteryECU status

banner "Fleet demo complete (${SECONDS}s)"
echo "All 3 ECUs updated via OTA cloud server in one orchestrated run."
