#!/usr/bin/env python3
"""
Installer/installer.py — Phase 10 OTA Installer

Usage:
    python3 Installer/installer.py packages/motor_ecu_v1.1.tar.gz
    python3 Installer/installer.py packages/motor_ecu_v1.1.tar.gz --activate --grace-duration 35
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "Tools")
sys.path.insert(0, TOOLS_DIR)

from verify_manifest import load_public_key, verify_checksum, verify_signature  # noqa: E402

VERSION_JSON = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "config", "version.json")
PENDING_VERSION_FILE = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "config", "pending_version.txt")
OTA_LOG_FILE = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "logs", "ota.log")


def ota_log(level, msg):
    os.makedirs(os.path.dirname(OTA_LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {level}  {msg}"
    print(line)
    with open(OTA_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _bootloader_path(custom_path=None):
    if custom_path:
        path = custom_path
    else:
        exe = ".exe" if os.name == "nt" else ""
        path = os.path.join(REPO_ROOT, f"Bootloader/build/bootloader{exe}")
    return path


def _health_monitor_path():
    exe = ".exe" if os.name == "nt" else ""
    return os.path.join(REPO_ROOT, f"Health_Monitor/build/health_monitor{exe}")


def _run_cmd(cmd, description):
    ota_log("INFO", description)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or "unknown error"
        ota_log("ERROR", f"{description} failed: {err}")
        raise RuntimeError(f"{description} failed:\n{err}")
    return result


def install_package(package_path, bootloader_path=None, activate=False, grace_duration=0):
    package_path = package_path if os.path.isabs(package_path) else os.path.join(REPO_ROOT, package_path)
    bl = _bootloader_path(bootloader_path)

    if not os.path.isfile(package_path):
        raise FileNotFoundError(f"Package not found: {package_path}")

    ota_log("INFO", f"Installing package: {package_path}")

    extract_dir = os.path.join(REPO_ROOT, "Tools/output/_install_tmp")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)

    with tarfile.open(package_path, "r:gz") as tar:
        tar.extractall(extract_dir)

    manifest_path = os.path.join(extract_dir, "manifest.json")
    binary_path = os.path.join(extract_dir, "firmware.bin")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    public_key = load_public_key(os.path.join(TOOLS_DIR, "keys/ota_public_key.pem"))

    ota_log("INFO", "Verifying Ed25519 signature")
    if not verify_signature(manifest, public_key):
        ota_log("ERROR", "REJECTED: manifest signature invalid")
        raise ValueError("REJECTED: manifest signature invalid — refusing to install")

    ota_log("INFO", "Verifying SHA-256 checksum")
    if not verify_checksum(binary_path, manifest):
        ota_log("ERROR", "REJECTED: binary checksum mismatch")
        raise ValueError("REJECTED: binary checksum mismatch — refusing to install")

    ota_log("INFO", f"Verification passed for {manifest['ecu']} v{manifest['version']}")

    _run_cmd([bl, "stage", binary_path], f"Bootloader stage v{manifest['version']}")

    if activate:
        os.makedirs(os.path.dirname(PENDING_VERSION_FILE), exist_ok=True)
        with open(PENDING_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(manifest["version"] + "\n")

        _run_cmd([bl, "activate"], f"Bootloader activate v{manifest['version']}")

        if grace_duration > 0:
            hm = _health_monitor_path()
            _run_cmd(
                [hm, "--grace", "--duration", str(grace_duration)],
                f"Health monitor grace period ({grace_duration}s)",
            )
        else:
            ota_log("INFO", "Activation complete (no grace monitoring requested)")

    ota_log("INFO", f"Install complete: {manifest['ecu']} v{manifest['version']}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Install a signed OTA firmware package")
    parser.add_argument("package", help="Path to .tar.gz package")
    parser.add_argument("--bootloader", default=None, help="Path to bootloader binary")
    parser.add_argument("--activate", action="store_true", help="Activate after staging")
    parser.add_argument(
        "--grace-duration",
        type=int,
        default=0,
        help="Run health monitor for N seconds after activation (requires --activate)",
    )
    args = parser.parse_args()

    try:
        install_package(
            args.package,
            bootloader_path=args.bootloader,
            activate=args.activate,
            grace_duration=args.grace_duration if args.activate else 0,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
