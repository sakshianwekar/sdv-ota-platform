#!/bin/bash

cd "$(dirname "$0")/.."

ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe"

echo "=============================="
echo "Starting Motor ECU..."
echo "=============================="

if [ ! -f "$ECU" ]; then
    echo "ERROR: Firmware not found!"
    exit 1
fi

echo "Firmware found."

exec "$ECU"