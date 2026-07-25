#!/usr/bin/env python3
"""
OTA_Cloud/server.py — Phase 13 FastAPI OTA server

Serves signed firmware packages from the packages/ directory.

Usage:
    uvicorn OTA_Cloud.server:app --host 0.0.0.0 --port 8080
"""

import json
import os
import sys
import tarfile

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))

from ota_log import ota_log  # noqa: E402

PACKAGES_DIR = os.path.join(REPO_ROOT, "packages")

app = FastAPI(
    title="SDV OTA Cloud",
    description="Local OTA server for signed Motor ECU firmware packages",
    version="1.0.0",
)


def _scan_packages():
    catalog = {}
    if not os.path.isdir(PACKAGES_DIR):
        return catalog

    for name in sorted(os.listdir(PACKAGES_DIR)):
        if not name.endswith(".tar.gz"):
            continue
        path = os.path.join(PACKAGES_DIR, name)
        try:
            with tarfile.open(path, "r:gz") as tar:
                manifest_member = tar.getmember("manifest.json")
                manifest_file = tar.extractfile(manifest_member)
                if manifest_file is None:
                    continue
                manifest = json.load(manifest_file)
        except (KeyError, json.JSONDecodeError, tarfile.TarError):
            continue

        ecu = manifest.get("ecu")
        version = manifest.get("version")
        if not ecu or not version:
            continue

        catalog.setdefault(ecu, {})[version] = {
            "ecu": ecu,
            "version": version,
            "size": manifest.get("size"),
            "checksum": manifest.get("checksum"),
            "package": name,
            "download_url": f"/packages/{ecu}/{version}",
        }

    return catalog


def _latest_for_ecu(ecu):
    catalog = _scan_packages()
    versions = catalog.get(ecu, {})
    if not versions:
        return None
    return max(versions.values(), key=lambda item: tuple(int(x) for x in item["version"].split(".")))


@app.get("/health")
def health():
    return {"status": "ok", "packages_dir": PACKAGES_DIR}


@app.get("/updates/{ecu}")
def list_updates(ecu):
    catalog = _scan_packages()
    if ecu not in catalog:
        raise HTTPException(status_code=404, detail=f"No packages found for ECU '{ecu}'")

    latest = _latest_for_ecu(ecu)
    ota_log("INFO", f"Update check for {ecu} — latest v{latest['version']}", component="cloud")
    return {
        "ecu": ecu,
        "latest": latest,
        "available": list(catalog[ecu].values()),
    }


@app.get("/packages/{ecu}/{version}")
def download_package(ecu, version):
    catalog = _scan_packages()
    entry = catalog.get(ecu, {}).get(version)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Package {ecu} v{version} not found")

    path = os.path.join(PACKAGES_DIR, entry["package"])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Package file missing on disk")

    ota_log("INFO", f"Serving {entry['package']}", component="cloud")
    return FileResponse(
        path,
        media_type="application/gzip",
        filename=entry["package"],
    )


@app.get("/catalog")
def full_catalog():
    return _scan_packages()
