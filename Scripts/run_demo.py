#!/usr/bin/env python3
"""
Scripts/run_demo.py — Cross-platform full OTA demo (Windows + macOS/Linux)

Replaces bash-only run_demo.sh logic for native testing without Docker.

Usage:
    python Scripts/run_demo.py
    python Scripts/run_demo.py --fast
    python Scripts/run_demo.py --cloud
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))
sys.path.insert(0, os.path.join(REPO_ROOT, "Installer"))

from platform_utils import (  # noqa: E402
    bootloader_path,
    exe_suffix,
    firmware_slot_filename,
    get_make_command,
    is_windows,
    resolve_binary_path,
    run_make,
)
from installer import install_package  # noqa: E402


def banner(msg):
    print()
    print("=" * 60)
    print(f"  {msg}")
    print("=" * 60)
    print()


def ensure_keys():
    subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "Tools", "gen_keys.py")],
        cwd=REPO_ROOT,
        check=True,
    )


def ensure_built(fast):
    if fast:
        print("FAST mode — skipping rebuild")
        return
    banner("Building components")
    dirs = [
        "Firmware/motor_ecu",
        "Firmware/motor_ecu_v1.1",
        "Firmware/motor_ecu_v1.2_broken",
        "Bootloader",
        "Health_Monitor",
    ]
    for d in dirs:
        run_make(os.path.join(REPO_ROOT, d), "rebuild")
    print("All components built.")


def kill_ecu_processes():
    pid_file = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "runtime", "ecu.pid")
    if os.path.isfile(pid_file):
        try:
            with open(pid_file, encoding="utf-8") as f:
                pid = int(f.read().strip())
            if is_windows():
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            else:
                subprocess.run(["kill", str(pid)], capture_output=True)
        except (ValueError, OSError):
            pass
        time.sleep(1)

    if is_windows():
        for img in ("motor_ecu.exe", "motor_ecu"):
            subprocess.run(["taskkill", "/F", "/IM", img], capture_output=True)
    else:
        subprocess.run(["pkill", "-f", "flash/slot"], capture_output=True)
    time.sleep(1)


def reset_to_v1_0():
    banner("Step 1: Reset to v1.0 on slotA")

    slot_a = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "flash", "slotA")
    slot_b = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "flash", "slotB")
    runtime = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "runtime")
    logs = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "logs")
    packages = os.path.join(REPO_ROOT, "packages")
    os.makedirs(slot_a, exist_ok=True)
    os.makedirs(slot_b, exist_ok=True)
    os.makedirs(runtime, exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    os.makedirs(packages, exist_ok=True)

    v1_0 = resolve_binary_path("Firmware/motor_ecu/build/motor_ecu")
    fw_name = firmware_slot_filename("motor_ecu")

    kill_ecu_processes()

    shutil.copy2(v1_0, os.path.join(slot_a, fw_name))
    shutil.copy2(v1_0, os.path.join(slot_b, fw_name))

    version_json = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "config", "version.json")
    with open(version_json, "w", encoding="utf-8") as f:
        json.dump(
            {"current_version": "1.0", "active_slot": "A", "pending_slot": None},
            f,
            indent=2,
        )
        f.write("\n")

    for rel in (
        "Virtual_ECU/MotorECU/config/pending_version.txt",
        "Virtual_ECU/MotorECU/config/previous_version.txt",
        "Virtual_ECU/MotorECU/logs/ota.log",
    ):
        path = os.path.join(REPO_ROOT, rel.replace("/", os.sep))
        if os.path.isfile(path):
            os.remove(path)

    # Start ECU
    ecu_bin = os.path.join(slot_a, fw_name)
    if is_windows():
        subprocess.Popen(
            [ecu_bin],
            cwd=REPO_ROOT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            [ecu_bin],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    time.sleep(2)
    print("Reset complete — running v1.0 on slotA")


def package_firmware(binary_rel, version):
    binary = resolve_binary_path(binary_rel)
    subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "Scripts", "package_generator.py"),
            binary,
            "--version",
            version,
            "--ecu",
            "MotorECU",
            "--out",
            os.path.join(REPO_ROOT, "packages"),
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def package_all():
    package_firmware("Firmware/motor_ecu/build/motor_ecu", "1.0")
    package_firmware("Firmware/motor_ecu_v1.1/build/motor_ecu", "1.1")
    package_firmware("Firmware/motor_ecu_v1.2_broken/build/motor_ecu", "1.2")


def install_local(package_name, grace):
    pkg = os.path.join(REPO_ROOT, "packages", package_name)
    install_package(pkg, activate=True, grace_duration=grace)


def install_cloud(server_url, version, grace):
    subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "OTA_Client", "client.py"),
            "--server",
            server_url,
            "--ecu",
            "MotorECU",
            "--version",
            version,
            "--activate",
            "--grace-duration",
            str(grace),
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def bootloader_status():
    bl = bootloader_path()
    subprocess.run([bl, "status"], cwd=REPO_ROOT, check=True)


def assert_final_version(expected="1.1"):
    version_json = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "config", "version.json")
    with open(version_json, encoding="utf-8") as f:
        actual = json.load(f)["current_version"]
    if actual != expected:
        raise SystemExit(f"ASSERT FAILED: expected version {expected}, got {actual}")
    print(f"ASSERT PASSED: final version is {expected}")


def start_ota_server(server_url):
    req_path = os.path.join(REPO_ROOT, "OTA_Cloud", "requirements.txt")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", req_path],
        cwd=REPO_ROOT,
        check=False,
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "OTA_Cloud.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(15):
        try:
            with urllib.request.urlopen(f"{server_url}/health", timeout=2) as resp:
                if resp.status == 200:
                    print(f"OTA server ready at {server_url} (PID {proc.pid})")
                    return proc
        except OSError:
            time.sleep(1)
    proc.kill()
    raise SystemExit("ERROR: OTA server failed to start")


def main():
    parser = argparse.ArgumentParser(description="SDV OTA full demo")
    parser.add_argument("--fast", action="store_true", help="Skip rebuild")
    parser.add_argument("--cloud", action="store_true", help="Use OTA cloud + client")
    parser.add_argument("--grace-v11", type=int, default=32)
    parser.add_argument("--grace-v12", type=int, default=12)
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    start = time.time()
    server_proc = None

    banner("SDV OTA Platform — Full Demo")
    print(f"Repo: {REPO_ROOT}")
    print(f"Platform: {'Windows' if is_windows() else 'Unix'}")
    if args.fast:
        print("Mode: FAST")
    if args.cloud:
        print("Mode: CLOUD")

    try:
        ensure_keys()
        ensure_built(args.fast)
        reset_to_v1_0()
        package_all()

        if args.cloud:
            server_proc = start_ota_server(args.server)

        banner("Step 2: Bootloader status")
        bootloader_status()

        banner("Step 3: OTA update v1.0 -> v1.1 (Eco Mode)")
        if args.cloud:
            install_cloud(args.server, "1.1", args.grace_v11)
        else:
            install_local("motorecu_v1.1.tar.gz", args.grace_v11)

        banner("Step 4: Confirm v1.1 healthy after grace period")
        bootloader_status()

        banner("Step 5: OTA update v1.1 -> v1.2-broken (expect rollback)")
        if args.cloud:
            install_cloud(args.server, "1.2", args.grace_v12)
        else:
            install_local("motorecu_v1.2.tar.gz", args.grace_v12)

        banner("Step 6: Final state (should be v1.1 after rollback)")
        bootloader_status()
        assert_final_version("1.1")

        banner("Step 7: OTA Log")
        ota_log = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "logs", "ota.log")
        if os.path.isfile(ota_log):
            with open(ota_log, encoding="utf-8") as f:
                print(f.read())
        else:
            print("(no ota.log written)")

        elapsed = int(time.time() - start)
        banner(f"Demo complete ({elapsed}s)")
        print("Expected outcome:")
        print("  - v1.1 installed and health-checked successfully")
        print("  - v1.2-broken detected and rolled back automatically")
        print("  - Final version: 1.1")
    finally:
        if server_proc:
            server_proc.terminate()


if __name__ == "__main__":
    main()
