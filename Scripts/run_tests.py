#!/usr/bin/env python3
"""Cross-platform tests runner (Windows + macOS/Linux)."""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = [
    "Tests/test_signing.py",
    "Tests/test_tamper.py",
    "Tests/test_downgrade.py",
]


def main():
    failed = 0
    for test in TESTS:
        print(f"\n--- Running {test} ---")
        result = subprocess.run([sys.executable, os.path.join(REPO_ROOT, test)], cwd=REPO_ROOT)
        if result.returncode != 0:
            failed += 1
    if failed:
        print(f"\n{failed} test suite(s) failed.")
        sys.exit(1)
    print("\nAll test suites passed.")


if __name__ == "__main__":
    main()
