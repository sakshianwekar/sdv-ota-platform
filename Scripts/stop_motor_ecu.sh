#!/bin/bash

echo "=============================="
echo "Stopping Motor ECU..."
echo "=============================="

pkill -f motor_ecu.exe

if [ $? -eq 0 ]; then
    echo "Motor ECU stopped successfully."
else
    echo "Motor ECU is not running."
fi