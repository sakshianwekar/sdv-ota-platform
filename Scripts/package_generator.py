#!/usr/bin/env python3
"""
Scripts/package_generator.py — Phase 9 OTA Package Generator

Usage:
    python3 Scripts/package_generator.py \\
        Firmware/motor_ecu_v1.1/build/motor_ecu \\
        --version 1.1 \\
        --ecu MotorECU \\
        --out packages/
"""

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))

from package_firmware import package_firmware  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Create a signed OTA firmware package")
    parser.add_argument("binary", help="Path to firmware binary")
    parser.add_argument("--version", required=True, help="Firmware version string")
    parser.add_argument("--ecu", required=True, help="ECU name (e.g. MotorECU)")
    parser.add_argument("--out", default="packages", help="Output directory")
    args = parser.parse_args()

    binary_path = args.binary
    if not os.path.isabs(binary_path):
        binary_path = os.path.join(REPO_ROOT, binary_path)

    out_dir = args.out
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(REPO_ROOT, out_dir)

    if not os.path.isfile(binary_path):
        print(f"ERROR: Binary not found: {binary_path}", file=sys.stderr)
        sys.exit(1)

    result = package_firmware(binary_path, args.version, args.ecu, out_dir)
    print(f"Package created: {result}")


if __name__ == "__main__":
    main()
