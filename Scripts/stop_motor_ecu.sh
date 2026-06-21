#!/bin/bash
cd "$(dirname "$0")/.."

ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe"
echo "=============================="
echo "Stopping Motor ECU..."
echo "=============================="

pkill -f $ECU

if [ $? -eq 0 ]; then
    echo "Motor ECU stopped successfully."
else
    echo "Motor ECU is not running."
fi