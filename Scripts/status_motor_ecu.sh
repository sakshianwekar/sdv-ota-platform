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
echo "Checking Motor ECU Status..."
echo "=============================="

if pgrep -f "$ECU" > /dev/null
then
    echo "Motor ECU Status : RUNNING"
else
    echo "Motor ECU Status : STOPPED"
fi
