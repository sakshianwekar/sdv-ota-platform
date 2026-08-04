"""Cross-platform paths and build helpers (Windows + macOS/Linux)."""

import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_windows():
    return os.name == "nt" or sys.platform == "win32"


def exe_suffix():
    return ".exe" if is_windows() else ""


def resolve_binary_path(path):
    """Resolve firmware/build binary path; append .exe on Windows if needed."""
    if os.path.isabs(path):
        full = path
    else:
        full = os.path.join(REPO_ROOT, path.replace("/", os.sep))

    if os.path.isfile(full):
        return full

    if is_windows() and not full.lower().endswith(".exe"):
        with_exe = full + ".exe"
        if os.path.isfile(with_exe):
            return with_exe

    return full


def bootloader_path(custom=None):
    if custom:
        return custom
    return os.path.join(REPO_ROOT, f"Bootloader/build/bootloader{exe_suffix()}")


def health_monitor_path():
    return os.path.join(REPO_ROOT, f"Health_Monitor/build/health_monitor{exe_suffix()}")


def firmware_slot_filename(base_name):
    """Flash slot filename (motor_ecu vs motor_ecu.exe)."""
    return base_name + exe_suffix()


def get_make_command():
    if is_windows():
        for cmd in ("mingw32-make", "make"):
            if shutil.which(cmd):
                return cmd
        return "mingw32-make"
    return "make"


def run_make(directory, target="all"):
    make = get_make_command()
    result = subprocess.run(
        [make, "-C", directory, target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Build failed: {make} -C {directory} {target}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def python_command():
    """Best Python launcher for the current platform."""
    if shutil.which("python3"):
        return "python3"
    if shutil.which("py"):
        return "py -3"
    return sys.executable
