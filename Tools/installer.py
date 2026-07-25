"""Backward-compatible wrapper — canonical installer is Installer/installer.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "Installer"))

from installer import install_package  # noqa: E402

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--bootloader", default=None)
    args = parser.parse_args()

    install_package(args.package, bootloader_path=args.bootloader)
