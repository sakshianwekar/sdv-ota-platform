#!/usr/bin/env python3
"""
OTA_Client/fleet.py — Phase 17 multi-ECU fleet orchestrator

Updates multiple ECUs (and optionally multiple vehicles) from the OTA cloud server.

Usage:
    python3 OTA_Client/fleet.py --server http://localhost:8080 --ecus MotorECU,BrakeECU,BatteryECU --version 1.1 --activate --grace-duration 20
    python3 OTA_Client/fleet.py --config Scripts/fleet_config.json --version 1.1 --activate
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))
sys.path.insert(0, os.path.join(REPO_ROOT, "Installer"))
sys.path.insert(0, os.path.join(REPO_ROOT, "OTA_Client"))

from ota_log import ota_log  # noqa: E402
from ecu_registry import list_ecus  # noqa: E402
from client import run_client  # noqa: E402


DEFAULT_FLEET = {
    "vehicles": [
        {
            "id": "VIN001",
            "ecus": ["MotorECU", "BrakeECU", "BatteryECU"],
        },
        {
            "id": "VIN002",
            "ecus": ["MotorECU", "BrakeECU", "BatteryECU"],
        },
    ]
}


def load_fleet_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_ecu_list(args):
    if args.ecus:
        return [e.strip() for e in args.ecus.split(",") if e.strip()]
    if args.config:
        config = load_fleet_config(args.config)
        ecus = []
        for vehicle in config.get("vehicles", []):
            ecus.extend(vehicle.get("ecus", []))
        return list(dict.fromkeys(ecus))
    return list_ecus()


def resolve_vehicles(args):
    if args.config:
        return load_fleet_config(args.config).get("vehicles", [])
    ecus = resolve_ecu_list(args)
    return [{"id": "VIN001", "ecus": ecus}]


def run_fleet(server_url, vehicles, version=None, activate=False, grace_duration=0):
    results = []
    total = sum(len(v.get("ecus", [])) for v in vehicles)

    ota_log("INFO", f"Fleet update starting — {len(vehicles)} vehicle(s), {total} ECU update(s)", component="fleet")

    for vehicle in vehicles:
        vin = vehicle.get("id", "unknown")
        ota_log("INFO", f"Vehicle {vin}: updating {len(vehicle.get('ecus', []))} ECU(s)", component="fleet")

        for ecu in vehicle.get("ecus", []):
            ota_log("INFO", f"[{vin}] Updating {ecu}", component="fleet", ecu=ecu)
            try:
                updated = run_client(
                    server_url,
                    ecu,
                    activate=activate,
                    grace_duration=grace_duration,
                    target_version=version,
                )
                status = "updated" if updated else "skipped"
                results.append({"vehicle": vin, "ecu": ecu, "status": status})
                ota_log("INFO", f"[{vin}] {ecu}: {status}", component="fleet", ecu=ecu)
            except (RuntimeError, ValueError, FileNotFoundError) as exc:
                results.append({"vehicle": vin, "ecu": ecu, "status": "failed", "error": str(exc)})
                ota_log("ERROR", f"[{vin}] {ecu} failed: {exc}", component="fleet", ecu=ecu)

    return results


def main():
    parser = argparse.ArgumentParser(description="Fleet OTA orchestrator — update multiple ECUs")
    parser.add_argument("--server", default="http://localhost:8080", help="OTA cloud server URL")
    parser.add_argument("--ecus", default=None, help="Comma-separated ECU names (e.g. MotorECU,BrakeECU)")
    parser.add_argument("--config", default=None, help="Fleet config JSON (Scripts/fleet_config.json)")
    parser.add_argument("--version", default=None, help="Target firmware version for all ECUs")
    parser.add_argument("--activate", action="store_true", help="Activate after staging")
    parser.add_argument("--grace-duration", type=int, default=0, help="Grace monitor seconds per ECU")
    args = parser.parse_args()

    vehicles = resolve_vehicles(args)

    try:
        results = run_fleet(
            args.server,
            vehicles,
            version=args.version,
            activate=args.activate,
            grace_duration=args.grace_duration,
        )
    except (RuntimeError, ValueError) as exc:
        ota_log("ERROR", str(exc), component="fleet")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    failed = [r for r in results if r["status"] == "failed"]
    updated = [r for r in results if r["status"] == "updated"]

    print("\n=== Fleet Update Summary ===")
    for row in results:
        detail = f"  {row['vehicle']} / {row['ecu']}: {row['status']}"
        if row.get("error"):
            detail += f" ({row['error']})"
        print(detail)

    print(f"\nUpdated: {len(updated)}  Failed: {len(failed)}  Total: {len(results)}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
