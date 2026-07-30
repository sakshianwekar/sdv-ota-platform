"""Central registry of supported virtual ECUs (Phase 16)."""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ECU_REGISTRY = {
    "MotorECU": {
        "firmware_binary": "motor_ecu",
        "firmware_dir": "Firmware/motor_ecu",
        "description": "Drive motor controller — RPM and temperature",
    },
    "BrakeECU": {
        "firmware_binary": "brake_ecu",
        "firmware_dir": "Firmware/brake_ecu",
        "description": "Brake-by-wire controller — pressure and temperature",
    },
    "BatteryECU": {
        "firmware_binary": "battery_ecu",
        "firmware_dir": "Firmware/battery_ecu",
        "description": "High-voltage battery manager — SOC and voltage",
    },
}


def list_ecus():
    return list(ECU_REGISTRY.keys())


def get_ecu_config(ecu_name):
    if ecu_name not in ECU_REGISTRY:
        raise ValueError(f"Unknown ECU '{ecu_name}'. Supported: {', '.join(list_ecus())}")
    return ECU_REGISTRY[ecu_name]


def ecu_paths(ecu_name):
    """Return absolute paths for an ECU's virtual flash/runtime/config."""
    get_ecu_config(ecu_name)
    base = os.path.join(REPO_ROOT, "Virtual_ECU", ecu_name)
    fw = ECU_REGISTRY[ecu_name]["firmware_binary"]
    return {
        "virtual_dir": base,
        "config_dir": os.path.join(base, "config"),
        "flash_a": os.path.join(base, "flash", "slotA", fw),
        "flash_b": os.path.join(base, "flash", "slotB", fw),
        "version_json": os.path.join(base, "config", "version.json"),
        "pending_version": os.path.join(base, "config", "pending_version.txt"),
        "heartbeat": os.path.join(base, "runtime", "heartbeat.txt"),
        "pidfile": os.path.join(base, "runtime", "ecu.pid"),
        "ota_log": os.path.join(base, "logs", "ota.log"),
        "firmware_binary": fw,
    }


def default_version_json():
    return {
        "current_version": "1.0",
        "active_slot": "A",
        "pending_slot": None,
    }
