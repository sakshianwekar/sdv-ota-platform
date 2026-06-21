#!/bin/bash
cd "$(dirname "$0")/.."

ECU="./Virtual_ECU/MotorECU/flash/slotA/motor_ecu.exe"
echo "=============================="
echo "Checking Motor ECU Status..."
echo "=============================="

if pgrep -f $ECU > /dev/null
then
    echo "Motor ECU Status : RUNNING"
else
    echo "Motor ECU Status : STOPPED"
fi