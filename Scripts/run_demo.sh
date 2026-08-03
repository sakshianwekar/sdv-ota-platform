#!/bin/bash
#
# Scripts/run_demo.sh — Full OTA demo (local installer path)
#
# Sequence:
#   1. Reset to v1.0 on slotA
#   2. Show bootloader status
#   3. Package + install v1.1 → stage → activate → grace period
#   4. Package + install v1.2-broken → stage → activate → auto rollback
#   5. Assert final state is v1.1 + print ota.log
#
# Options:
#   FAST=1     Skip rebuild (for recording — target ~60s runtime)
#   CLOUD=1    Use OTA client + FastAPI server instead of direct installer
#
# Run from repo root (or via docker compose run dev bash).

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

BL="$REPO_ROOT/Bootloader/build/bootloader"
V1_0="$REPO_ROOT/Firmware/motor_ecu/build/motor_ecu"
V1_1="$REPO_ROOT/Firmware/motor_ecu_v1.1/build/motor_ecu"
V1_2="$REPO_ROOT/Firmware/motor_ecu_v1.2_broken/build/motor_ecu"
SLOT_A="$REPO_ROOT/Virtual_ECU/MotorECU/flash/slotA"
SLOT_B="$REPO_ROOT/Virtual_ECU/MotorECU/flash/slotB"
VERSION_JSON="$REPO_ROOT/Virtual_ECU/MotorECU/config/version.json"
OTA_LOG="$REPO_ROOT/Virtual_ECU/MotorECU/logs/ota.log"
PACKAGES="$REPO_ROOT/packages"

# Grace timings — tuned so rollback completes before monitor exit (~90s with build skipped)
GRACE_V11="${GRACE_V11:-32}"
GRACE_V12="${GRACE_V12:-12}"
SERVER_URL="${SERVER_URL:-http://localhost:8080}"

banner() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

ensure_keys() {
    if [ ! -f "$REPO_ROOT/Tools/keys/ota_signing_key.pem" ]; then
        echo "Generating signing keys..."
        python3 "$REPO_ROOT/Tools/gen_keys.py"
    fi
}

ensure_built() {
    if [ "${FAST:-0}" = "1" ]; then
        echo "FAST=1 — skipping rebuild"
        return
    fi
    banner "Building components"
    make -C "$REPO_ROOT/Firmware/motor_ecu" rebuild
    make -C "$REPO_ROOT/Firmware/motor_ecu_v1.1" rebuild
    make -C "$REPO_ROOT/Firmware/motor_ecu_v1.2_broken" rebuild
    make -C "$REPO_ROOT/Bootloader" rebuild
    make -C "$REPO_ROOT/Health_Monitor" rebuild
    echo "All components built."
}

reset_to_v1_0() {
    banner "Step 1: Reset to v1.0 on slotA"

    mkdir -p "$SLOT_A" "$SLOT_B" \
        "$REPO_ROOT/Virtual_ECU/MotorECU/runtime" \
        "$REPO_ROOT/Virtual_ECU/MotorECU/logs" \
        "$PACKAGES"

    if [ -f "$REPO_ROOT/Virtual_ECU/MotorECU/runtime/ecu.pid" ]; then
        PID=$(cat "$REPO_ROOT/Virtual_ECU/MotorECU/runtime/ecu.pid" 2>/dev/null || true)
        if [ -n "$PID" ]; then
            kill "$PID" 2>/dev/null || true
            sleep 1
        fi
    fi
    pkill -f "flash/slot" 2>/dev/null || true

    cp "$V1_0" "$SLOT_A/motor_ecu"
    cp "$V1_0" "$SLOT_B/motor_ecu"
    chmod +x "$SLOT_A/motor_ecu" "$SLOT_B/motor_ecu"

    cat > "$VERSION_JSON" <<'EOF'
{
  "current_version": "1.0",
  "active_slot":     "A",
  "pending_slot":    null
}
EOF

    rm -f "$REPO_ROOT/Virtual_ECU/MotorECU/config/pending_version.txt"
    rm -f "$REPO_ROOT/Virtual_ECU/MotorECU/config/previous_version.txt"
    rm -f "$OTA_LOG"

    "$SLOT_A/motor_ecu" > /dev/null 2>&1 &
    sleep 2

    echo "Reset complete — running v1.0 on slotA"
}

package_all() {
    python3 "$REPO_ROOT/Scripts/package_generator.py" \
        "$V1_0" --version 1.0 --ecu MotorECU --out "$PACKAGES"
    python3 "$REPO_ROOT/Scripts/package_generator.py" \
        "$V1_1" --version 1.1 --ecu MotorECU --out "$PACKAGES"
    python3 "$REPO_ROOT/Scripts/package_generator.py" \
        "$V1_2" --version 1.2 --ecu MotorECU --out "$PACKAGES"
}

install_v11() {
    if [ "${CLOUD:-0}" = "1" ]; then
        python3 "$REPO_ROOT/OTA_Client/client.py" \
            --server "$SERVER_URL" --ecu MotorECU --version 1.1 \
            --activate --grace-duration "$GRACE_V11"
    else
        python3 "$REPO_ROOT/Installer/installer.py" \
            "$PACKAGES/motorecu_v1.1.tar.gz" \
            --activate --grace-duration "$GRACE_V11"
    fi
}

install_v12() {
    if [ "${CLOUD:-0}" = "1" ]; then
        python3 "$REPO_ROOT/OTA_Client/client.py" \
            --server "$SERVER_URL" --ecu MotorECU --version 1.2 \
            --activate --grace-duration "$GRACE_V12"
    else
        python3 "$REPO_ROOT/Installer/installer.py" \
            "$PACKAGES/motorecu_v1.2.tar.gz" \
            --activate --grace-duration "$GRACE_V12"
    fi
}

assert_final_version() {
    local expected="1.1"
    local actual
    actual=$(python3 -c "import json; print(json.load(open('$VERSION_JSON'))['current_version'])")
    if [ "$actual" != "$expected" ]; then
        echo "ASSERT FAILED: expected version $expected, got $actual"
        exit 1
    fi
    echo "ASSERT PASSED: final version is $expected"
}

start_ota_server() {
    if [ "${CLOUD:-0}" != "1" ]; then
        return
    fi
    pip3 install -q -r "$REPO_ROOT/OTA_Cloud/requirements.txt" 2>/dev/null || true
    uvicorn OTA_Cloud.server:app --host 127.0.0.1 --port 8080 > /tmp/ota_server.log 2>&1 &
    SERVER_PID=$!
    sleep 2
    for _ in $(seq 1 10); do
        if curl -sf "$SERVER_URL/health" > /dev/null 2>&1; then
            echo "OTA server ready at $SERVER_URL (PID $SERVER_PID)"
            return
        fi
        sleep 1
    done
    echo "ERROR: OTA server failed to start"
    cat /tmp/ota_server.log || true
    exit 1
}

stop_ota_server() {
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}

trap stop_ota_server EXIT

SECONDS=0
banner "SDV OTA Platform — Full Demo"
echo "Repo: $REPO_ROOT"
[ "${FAST:-0}" = "1" ] && echo "Mode: FAST (no rebuild)"
[ "${CLOUD:-0}" = "1" ] && echo "Mode: CLOUD (FastAPI + OTA client)"

ensure_keys
ensure_built
reset_to_v1_0
package_all
start_ota_server

banner "Step 2: Bootloader status"
"$BL" status

banner "Step 3: OTA update v1.0 → v1.1 (Eco Mode)"
install_v11

banner "Step 4: Confirm v1.1 healthy after grace period"
"$BL" status

banner "Step 5: OTA update v1.1 → v1.2-broken (expect rollback)"
install_v12

banner "Step 6: Final state (should be v1.1 after rollback)"
"$BL" status
assert_final_version

banner "Step 7: OTA Log"
if [ -f "$OTA_LOG" ]; then
    cat "$OTA_LOG"
else
    echo "(no ota.log written)"
fi

banner "Demo complete (${SECONDS}s)"
echo "Expected outcome:"
echo "  - v1.1 installed and health-checked successfully"
echo "  - v1.2-broken detected and rolled back automatically"
echo "  - Final version: 1.1 on previous slot"
