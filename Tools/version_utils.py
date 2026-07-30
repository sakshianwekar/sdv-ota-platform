"""Version comparison helpers for downgrade protection."""

import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from ecu_registry import ecu_paths  # noqa: E402


def parse_version(version_str):
    parts = str(version_str).strip().split(".")
    result = []
    for part in parts:
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        result.append(int(digits or "0"))
    return tuple(result)


def compare_versions(a, b):
    """Return -1 if a<b, 0 if equal, 1 if a>b."""
    av = parse_version(a)
    bv = parse_version(b)
    length = max(len(av), len(bv))
    av = av + (0,) * (length - len(av))
    bv = bv + (0,) * (length - len(bv))
    if av < bv:
        return -1
    if av > bv:
        return 1
    return 0


def is_downgrade(current_version, new_version):
    return compare_versions(new_version, current_version) < 0


def read_current_version(ecu="MotorECU", path=None):
    version_json = path or ecu_paths(ecu)["version_json"]
    with open(version_json, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("current_version", "0.0")
