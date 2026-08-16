#!/bin/bash
cd "$(dirname "$0")/.."

if [ -f "./Virtual_ECU/MotorECU/flash/slotA/motor_ecu" ]; then
    ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu"
elif [ -f "./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe" ]; then
    ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe"
else
    ECU="flash/slotA/motor_ecu"
fi

echo "=============================="
echo "Stopping Motor ECU..."
echo "=============================="

if pkill -f "$ECU"; then
    echo "Motor ECU stopped successfully."
else
    echo "Motor ECU is not running."
fi
