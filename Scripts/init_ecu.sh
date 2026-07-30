#!/bin/bash
#
# Scripts/init_ecu.sh — Initialize a virtual ECU to v1.0 on slotA
#
# Usage:
#   ./Scripts/init_ecu.sh MotorECU
#   ./Scripts/init_ecu.sh BrakeECU
#   ./Scripts/init_ecu.sh BatteryECU
#   ./Scripts/init_ecu.sh all
#
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

init_one() {
    local ecu="$1"
    local fw_dir fw_bin slot_a slot_b

    case "$ecu" in
        MotorECU)
            fw_dir="Firmware/motor_ecu"
            fw_bin="motor_ecu"
            ;;
        BrakeECU)
            fw_dir="Firmware/brake_ecu"
            fw_bin="brake_ecu"
            ;;
        BatteryECU)
            fw_dir="Firmware/battery_ecu"
            fw_bin="battery_ecu"
            ;;
        *)
            echo "Unknown ECU: $ecu"
            exit 1
            ;;
    esac

    local base="$REPO_ROOT/Virtual_ECU/$ecu"
    slot_a="$base/flash/slotA"
    slot_b="$base/flash/slotB"

    mkdir -p "$slot_a" "$slot_b" "$base/config" "$base/runtime" "$base/logs"

    local binary="$REPO_ROOT/$fw_dir/build/$fw_bin"
    if [ ! -f "$binary" ]; then
        echo "Building $ecu firmware..."
        make -C "$REPO_ROOT/$fw_dir" rebuild
    fi

    cp "$binary" "$slot_a/$fw_bin"
    cp "$binary" "$slot_b/$fw_bin"

    cat > "$base/config/version.json" <<'EOF'
{
  "current_version": "1.0",
  "active_slot": "A",
  "pending_slot": null
}
EOF

    rm -f "$base/config/pending_version.txt" "$base/config/previous_version.txt"

    if [ -f "$base/runtime/ecu.pid" ]; then
        pid=$(cat "$base/runtime/ecu.pid" 2>/dev/null || true)
        if [ -n "${pid:-}" ]; then
            kill "$pid" 2>/dev/null || true
            sleep 1
        fi
    fi

    "$slot_a/$fw_bin" > /dev/null 2>&1 &
    sleep 1
    echo "Initialized $ecu — v1.0 on slotA"
}

if [ "${1:-}" = "all" ]; then
    init_one MotorECU
    init_one BrakeECU
    init_one BatteryECU
elif [ -n "${1:-}" ]; then
    init_one "$1"
else
    echo "Usage: $0 {MotorECU|BrakeECU|BatteryECU|all}"
    exit 1
fi
