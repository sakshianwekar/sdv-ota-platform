#!/usr/bin/env python3
"""Tests tampered package rejection."""

import copy
import json
import os
import shutil
import sys
import tarfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))
sys.path.insert(0, os.path.join(REPO_ROOT, "Installer"))

from sign_manifest import build_and_sign_manifest, load_private_key  # noqa: E402
from verify_manifest import load_public_key, verify_checksum, verify_signature  # noqa: E402

priv = load_private_key(os.path.join(REPO_ROOT, "Tools/keys/ota_signing_key.pem"))
pub = load_public_key(os.path.join(REPO_ROOT, "Tools/keys/ota_public_key.pem"))

binary = os.path.join(REPO_ROOT, "Firmware/motor_ecu_v1.1/build/motor_ecu")
if not os.path.isfile(binary):
    print(f"SKIP: binary not built ({binary})")
    sys.exit(0)

manifest = build_and_sign_manifest(binary, "1.1", "MotorECU", priv)
assert verify_signature(manifest, pub)
assert verify_checksum(binary, manifest)

tampered_manifest = copy.deepcopy(manifest)
tampered_manifest["checksum"] = "sha256:" + "0" * 64
assert verify_signature(tampered_manifest, pub) is False

# Build a tarball with a flipped firmware byte
tmpdir = os.path.join(REPO_ROOT, "Tools/output/_tamper_tmp")
if os.path.exists(tmpdir):
    shutil.rmtree(tmpdir)
os.makedirs(tmpdir)

shutil.copy(binary, os.path.join(tmpdir, "firmware.bin"))
with open(os.path.join(tmpdir, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f)

tampered_pkg = os.path.join(REPO_ROOT, "Tools/output/tampered.tar.gz")
with tarfile.open(tampered_pkg, "w:gz") as tar:
    tar.add(os.path.join(tmpdir, "firmware.bin"), arcname="firmware.bin")
    tar.add(os.path.join(tmpdir, "manifest.json"), arcname="manifest.json")

# Flip one byte in the packaged binary
with tarfile.open(tampered_pkg, "r:gz") as tar:
    tar.extractall(tmpdir)
with open(os.path.join(tmpdir, "firmware.bin"), "r+b") as f:
    b = f.read(1)
    f.seek(0)
    f.write(bytes([b[0] ^ 0xFF]))
with tarfile.open(tampered_pkg, "w:gz") as tar:
    tar.add(os.path.join(tmpdir, "firmware.bin"), arcname="firmware.bin")
    tar.add(os.path.join(tmpdir, "manifest.json"), arcname="manifest.json")

from installer import install_package  # noqa: E402

try:
    install_package(tampered_pkg)
    print("FAIL: tampered package was accepted")
    sys.exit(1)
except ValueError as exc:
    assert "checksum" in str(exc).lower() or "signature" in str(exc).lower()
    print(f"PASS: tampered package correctly rejected - {exc}")

print("All tamper rejection tests passed.")
