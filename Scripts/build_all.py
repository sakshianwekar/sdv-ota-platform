#!/usr/bin/env python3
"""Build all platform components (Windows + macOS/Linux)."""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))

from platform_utils import get_make_command, run_make  # noqa: E402

COMPONENTS = [
    "Firmware/motor_ecu",
    "Firmware/motor_ecu_v1.1",
    "Firmware/motor_ecu_v1.2_broken",
    "Firmware/brake_ecu",
    "Firmware/battery_ecu",
    "Bootloader",
    "Health_Monitor",
]


def main():
    print(f"Using make: {get_make_command()}")
    for component in COMPONENTS:
        path = os.path.join(REPO_ROOT, component)
        print(f"Building {component}...")
        run_make(path, "rebuild")
        print(f"  OK")
    print("All components built successfully.")


if __name__ == "__main__":
    main()
