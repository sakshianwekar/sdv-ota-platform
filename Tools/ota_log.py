"""Shared structured logging for OTA Python components."""

import os
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from ecu_registry import ecu_paths  # noqa: E402


def _safe_print(line):
    try:
        print(line)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(line.encode(encoding, errors="replace").decode(encoding))


def ota_log(level, msg, component="ota", ecu="MotorECU"):
    log_file = ecu_paths(ecu)["ota_log"]
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {level}  [{component}] {msg}"
    _safe_print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")
