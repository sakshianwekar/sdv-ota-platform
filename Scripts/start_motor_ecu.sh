#!/bin/bash

cd "$(dirname "$0")/.."

if [ -f "./Virtual_ECU/MotorECU/flash/slotA/motor_ecu" ]; then
    ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu"
elif [ -f "./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe" ]; then
    ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe"
else
    echo "ERROR: Firmware not found in slotA!"
    exit 1
fi

echo "=============================="
echo "Starting Motor ECU..."
echo "=============================="
echo "Firmware: $ECU"

exec "$ECU"