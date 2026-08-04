@echo off
REM Windows launcher for full OTA demo
cd /d "%~dp0\.."
if "%FAST%"=="1" (
    py -3 Scripts\run_demo.py --fast
) else if "%CLOUD%"=="1" (
    py -3 Scripts\run_demo.py --cloud
) else (
    py -3 Scripts\run_demo.py
)
