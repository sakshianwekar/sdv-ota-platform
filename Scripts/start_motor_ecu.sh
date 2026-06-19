#!/bin/bash

ECU_PATH="../Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe"

echo "=============================="
echo "Starting Motor ECU..."
echo "=============================="

if [ ! -f "$ECU_PATH" ]; then
    echo "ERROR: Firmware not found!"
    exit 1
fi

echo "Firmware found."

"$ECU_PATH"