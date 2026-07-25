#!/bin/bash
#
# Scripts/run_demo.sh — Phase 12 full OTA demo
#
# Sequence:
#   1. Reset to v1.0 on slotA
#   2. Show bootloader status
#   3. Package + install v1.1 → stage → activate → grace period
#   4. Package + install v1.2-broken → stage → activate → auto rollback
#   5. Show final state + ota.log
#
# Run from repo root (or via docker compose run dev bash).

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

BL="$REPO_ROOT/Bootloader/build/bootloader"
HM="$REPO_ROOT/Health_Monitor/build/health_monitor"
V1_0="$REPO_ROOT/Firmware/motor_ecu/build/motor_ecu"
V1_1="$REPO_ROOT/Firmware/motor_ecu_v1.1/build/motor_ecu"
V1_2="$REPO_ROOT/Firmware/motor_ecu_v1.2_broken/build/motor_ecu"
SLOT_A="$REPO_ROOT/Virtual_ECU/MotorECU/flash/slotA"
SLOT_B="$REPO_ROOT/Virtual_ECU/MotorECU/flash/slotB"
VERSION_JSON="$REPO_ROOT/Virtual_ECU/MotorECU/config/version.json"
OTA_LOG="$REPO_ROOT/Virtual_ECU/MotorECU/logs/ota.log"
PACKAGES="$REPO_ROOT/packages"

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
        "$REPO_ROOT/Virtual_ECU/MotorECU/logs"

    # Stop any running ECU
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

    # Start ECU from slotA
    "$SLOT_A/motor_ecu" > /dev/null 2>&1 &
    sleep 2

    echo "Reset complete — running v1.0 on slotA"
}

banner "SDV OTA Platform — Full Demo"
echo "Repo: $REPO_ROOT"

ensure_keys
ensure_built
reset_to_v1_0

banner "Step 2: Bootloader status"
"$BL" status

banner "Step 3: OTA update v1.0 → v1.1 (Eco Mode)"
python3 "$REPO_ROOT/Scripts/package_generator.py" \
    "$V1_1" --version 1.1 --ecu MotorECU --out "$PACKAGES"

python3 "$REPO_ROOT/Installer/installer.py" \
    "$PACKAGES/motorecu_v1.1.tar.gz" \
    --activate --grace-duration 35

banner "Step 4: Confirm v1.1 healthy after grace period"
"$BL" status
echo "v1.1 activation confirmed."

banner "Step 5: OTA update v1.1 → v1.2-broken (expect rollback)"
python3 "$REPO_ROOT/Scripts/package_generator.py" \
    "$V1_2" --version 1.2 --ecu MotorECU --out "$PACKAGES"

python3 "$REPO_ROOT/Installer/installer.py" \
    "$PACKAGES/motorecu_v1.2.tar.gz" \
    --activate --grace-duration 15

banner "Step 6: Final state (should be v1.1 after rollback)"
"$BL" status

banner "Step 7: OTA Log"
if [ -f "$OTA_LOG" ]; then
    cat "$OTA_LOG"
else
    echo "(no ota.log written)"
fi

banner "Demo complete"
echo "Expected outcome:"
echo "  - v1.1 installed and health-checked successfully"
echo "  - v1.2-broken detected and rolled back automatically"
echo "  - Final version: 1.1 on previous slot"
