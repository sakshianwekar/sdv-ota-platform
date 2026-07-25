#!/usr/bin/env python3
"""
OTA_Client/client.py — Phase 14 OTA client

Polls the OTA cloud server, downloads signed packages, verifies them,
and installs via the Installer.

Usage:
    python3 OTA_Client/client.py --server http://localhost:8080 --ecu MotorECU
    python3 OTA_Client/client.py --server http://localhost:8080 --ecu MotorECU --activate --grace-duration 35
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))
sys.path.insert(0, os.path.join(REPO_ROOT, "Installer"))

from ota_log import ota_log  # noqa: E402
from version_utils import compare_versions, read_current_version  # noqa: E402
from installer import install_package  # noqa: E402


def _get_json(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def _download(url, dest_path):
    urllib.request.urlretrieve(url, dest_path)


def poll_for_update(server_url, ecu, target_version=None):
    current = read_current_version()
    ota_log("INFO", f"Current ECU version: {current}", component="client")

    updates_url = f"{server_url.rstrip('/')}/updates/{ecu}"
    try:
        data = _get_json(updates_url)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Update check failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach OTA server at {server_url}: {exc.reason}") from exc

    if target_version:
        update = next(
            (item for item in data.get("available", []) if item["version"] == target_version),
            None,
        )
        if update is None:
            raise RuntimeError(f"Version {target_version} not available on server for {ecu}")
    else:
        update = data["latest"]

    latest_version = update["version"]

    if compare_versions(latest_version, current) <= 0:
        ota_log("INFO", f"No update available (current={current}, target={latest_version})", component="client")
        return None

    ota_log("INFO", f"Update available: {current} → {latest_version}", component="client")
    return update


def download_and_install(server_url, update_info, activate=False, grace_duration=0):
    download_url = f"{server_url.rstrip('/')}{update_info['download_url']}"
    ota_log("INFO", f"Downloading {download_url}", component="client")

    os.makedirs(os.path.join(REPO_ROOT, "packages"), exist_ok=True)
    local_name = update_info.get("package") or f"{update_info['ecu'].lower()}_v{update_info['version']}.tar.gz"
    local_path = os.path.join(REPO_ROOT, "packages", local_name)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
        tmp_path = tmp.name

    try:
        _download(download_url, tmp_path)
        os.replace(tmp_path, local_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    ota_log("INFO", f"Downloaded to {local_path}", component="client")
    return install_package(
        local_path,
        activate=activate,
        grace_duration=grace_duration if activate else 0,
    )


def run_client(server_url, ecu, activate=False, grace_duration=0, target_version=None):
    update = poll_for_update(server_url, ecu, target_version=target_version)
    if update is None:
        return False

    download_and_install(server_url, update, activate=activate, grace_duration=grace_duration)
    return True


def main():
    parser = argparse.ArgumentParser(description="OTA client — poll, download, verify, install")
    parser.add_argument("--server", default="http://localhost:8080", help="OTA cloud server URL")
    parser.add_argument("--ecu", default="MotorECU", help="ECU name")
    parser.add_argument("--activate", action="store_true", help="Activate after staging")
    parser.add_argument("--grace-duration", type=int, default=0, help="Grace monitor seconds (requires --activate)")
    parser.add_argument("--version", default=None, help="Install a specific package version")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    args = parser.parse_args()

    try:
        updated = run_client(
            args.server,
            args.ecu,
            activate=args.activate,
            grace_duration=args.grace_duration,
            target_version=args.version,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        ota_log("ERROR", str(exc), component="client")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if not updated:
        sys.exit(0)


if __name__ == "__main__":
    main()
