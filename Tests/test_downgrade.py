#!/usr/bin/env python3
"""Tests downgrade protection in the installer."""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Tools"))
sys.path.insert(0, os.path.join(REPO_ROOT, "Installer"))

from version_utils import is_downgrade, compare_versions  # noqa: E402

assert compare_versions("1.0", "1.1") == -1
assert compare_versions("1.2", "1.1") == 1
assert compare_versions("1.1", "1.1") == 0
assert is_downgrade("1.1", "1.0") is True
assert is_downgrade("1.1", "1.2") is False
assert is_downgrade("1.1", "1.1") is False

# Integration: attempt to install v1.0 while current is v1.1
version_json = os.path.join(REPO_ROOT, "Virtual_ECU", "MotorECU", "config", "version.json")
package_v10 = os.path.join(REPO_ROOT, "packages", "motorecu_v1.0.tar.gz")

if os.path.isfile(package_v10):
    backup = None
    with open(version_json, encoding="utf-8") as f:
        backup = json.load(f)

    with open(version_json, "w", encoding="utf-8") as f:
        json.dump({**backup, "current_version": "1.1"}, f, indent=2)

    from installer import install_package  # noqa: E402

    try:
        install_package(package_v10)
        print("FAIL: downgrade package was accepted")
        sys.exit(1)
    except ValueError as exc:
        assert "downgrade" in str(exc).lower()
        print(f"PASS: downgrade correctly rejected — {exc}")
    finally:
        with open(version_json, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=2)
else:
    print("SKIP: motorecu_v1.0.tar.gz not found — unit checks only")

print("All downgrade protection tests passed.")
