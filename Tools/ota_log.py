"""Shared structured logging for OTA Python components."""

import os
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OTA_LOG_FILE = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "logs", "ota.log")


def ota_log(level, msg, component="ota"):
    os.makedirs(os.path.dirname(OTA_LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {level}  [{component}] {msg}"
    print(line)
    with open(OTA_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
