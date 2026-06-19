#!/bin/bash

echo "=============================="
echo "Checking Motor ECU Status..."
echo "=============================="

if pgrep -f motor_ecu.exe > /dev/null
then
    echo "Motor ECU Status : RUNNING"
else
    echo "Motor ECU Status : STOPPED"
fi