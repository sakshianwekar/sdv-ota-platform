# SDV OTA Platform — Architecture & Code Flow

This document explains what the project does, how the components fit together, and what happens at each step during an OTA update.

---

## What This Project Is

**sdv-ota-platform** is a software-only simulation of an automotive **Over-The-Air (OTA) firmware update** system. It models patterns used in production vehicle ECU updates:

- **A/B slot firmware** — never overwrite the running image
- **Ed25519-signed packages** — cryptographic authenticity + SHA-256 integrity
- **Grace-period health monitoring** — automatic rollback on consecutive heartbeat failures
- **Downgrade protection** — reject older firmware before staging

No real hardware, database, or message queue is required. All state lives on the filesystem (`version.json`, flash slot binaries, heartbeat files, `ota.log`).

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  OTA_Cloud (FastAPI)                                                │
│  Serves signed .tar.gz packages from packages/                      │
│  GET /health, /updates/{ecu}, /packages/{ecu}/{version}, /catalog   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP (poll + download)
┌───────────────────────────────▼─────────────────────────────────────┐
│  OTA_Client (Python)                                                │
│  Poll server → compare versions → download → call Installer       │
│  fleet.py orchestrates multiple ECUs / vehicles                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│  Installer (Python)                                                 │
│  Extract tarball → verify signature + checksum → downgrade check    │
│  → bootloader stage → (optional) activate → health monitor          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ subprocess
┌───────────────────────────────▼─────────────────────────────────────┐
│  Bootloader (C) — ONLY writer to flash slots                        │
│  stage → inactive slot | activate → flip slot + restart ECU         │
│  rollback → flip back + restore previous version                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ launches binary from active slot
┌───────────────────────────────▼─────────────────────────────────────┐
│  Virtual ECU firmware (C process)                                   │
│  slotA/ + slotB/ binaries, heartbeat.txt, ecu.pid                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ heartbeat every 1s
┌───────────────────────────────▼─────────────────────────────────────┐
│  Health_Monitor (C)                                                 │
│  3 consecutive failures in grace window → bootloader rollback       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
sdv-ota-platform/
├── OTA_Cloud/           # FastAPI server — package catalog + downloads
├── OTA_Client/          # Polling client + fleet orchestrator
├── Installer/           # Verify, stage, activate pipeline
├── Bootloader/          # A/B slot manager (C)
├── Health_Monitor/      # Post-activation watchdog (C)
├── Firmware/            # Simulated ECU binaries (motor, brake, battery)
├── Virtual_ECU/         # Per-ECU flash slots, config, runtime, logs
│   ├── MotorECU/
│   ├── BrakeECU/
│   └── BatteryECU/
├── Common/version_store/# Shared C library for version.json I/O
├── Tools/               # Keys, signing, packaging, ECU registry, logging
├── Scripts/             # Demo scripts, init, packaging helpers
└── Tests/               # Security + downgrade integration tests
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| ECU firmware | C (gcc, Make) |
| Bootloader / Health Monitor | C (gcc, Make) |
| Version state | JSON files via hand-rolled C parser (`version_store`) |
| OTA cloud | Python 3, FastAPI, uvicorn |
| Client / Installer / Tools | Python 3, cryptography (Ed25519) |
| Containerization | Docker (Ubuntu 24.04), docker-compose |
| Package format | `.tar.gz` containing `firmware.bin` + `manifest.json` |

---

## Virtual ECU Layout

Each ECU (MotorECU, BrakeECU, BatteryECU) has an identical directory structure:

```
Virtual_ECU/MotorECU/
├── flash/
│   ├── slotA/motor_ecu    # Firmware binary in slot A
│   └── slotB/motor_ecu    # Firmware binary in slot B
├── config/
│   ├── version.json       # {current_version, active_slot, pending_slot}
│   ├── pending_version.txt
│   └── previous_version.txt
├── runtime/
│   ├── heartbeat.txt      # Unix timestamp, updated every 1s
│   └── ecu.pid            # PID of running ECU process
└── logs/
    └── ota.log            # Structured OTA event log
```

The **bootloader is the only component** that writes to `flash/slotA` and `flash/slotB`. The installer never touches slot binaries directly.

---

## OTA Package Format

Packages are signed `.tar.gz` archives:

```
motorecu_v1.1.tar.gz
├── firmware.bin      # ECU binary
└── manifest.json     # {version, ecu, size, checksum, signature}
```

Signing details are documented in [signing.md](./signing.md).

- **Private key:** `Tools/keys/ota_signing_key.pem` (gitignored, generated locally)
- **Public key:** `Tools/keys/ota_public_key.pem` (committed, used by installer for verification)

---

## Component Responsibilities

### OTA_Cloud (`OTA_Cloud/server.py`)

- Scans `packages/` for `.tar.gz` files
- Reads `manifest.json` inside each package to build a catalog
- Exposes REST endpoints for health checks, update discovery, and downloads

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Server health + packages directory path |
| `GET /updates/{ecu}` | Latest and all available packages for an ECU |
| `GET /packages/{ecu}/{version}` | Download signed package |
| `GET /catalog` | Full package catalog for all ECUs |

### OTA_Client (`OTA_Client/client.py`, `fleet.py`)

**client.py** — single-ECU update flow:

1. Read current version from `version.json`
2. `GET /updates/{ecu}` from cloud server
3. Compare versions; skip if no update available
4. Download package to `packages/`
5. Delegate to `Installer/installer.py`

**fleet.py** — iterates over multiple ECUs (and optionally multiple vehicles via `Scripts/fleet_config.json`).

### Installer (`Installer/installer.py`)

The core on-device install pipeline:

1. **Extract** tarball to a temp directory
2. **Verify Ed25519 signature** on manifest (authenticity)
3. **Verify SHA-256 checksum** of `firmware.bin` (integrity)
4. **Downgrade check** — reject if `new_version < current_version`
5. **Stage** — call `bootloader stage <binary>` (writes to inactive slot)
6. **Activate** (optional) — write `pending_version.txt`, call `bootloader activate`
7. **Health monitor** (optional) — run grace-period watch after activation

### Bootloader (`Bootloader/`)

CLI commands (run from repo root):

| Command | What it does |
|---------|--------------|
| `status` | Print current version, active/pending slots |
| `stage <path>` | Copy firmware binary to the **inactive** slot |
| `activate` | Flip active slot, kill old ECU process, start new binary |
| `rollback` | Flip back to previous slot, restore previous version |

Uses `Common/version_store/` for atomic read/write of `version.json`.

### Health_Monitor (`Health_Monitor/`)

Watches `heartbeat.txt` after activation:

| Constant | Value | Meaning |
|----------|-------|---------|
| `HEARTBEAT_TIMEOUT` | 5s | Heartbeat considered stale after this |
| `GRACE_PERIOD_SECONDS` | 30s | Default watch window after activation |
| `FAILURE_THRESHOLD` | 3 | Consecutive failures before rollback |

During the grace period, 3 consecutive heartbeat failures trigger `bootloader rollback` automatically.

### Firmware (`Firmware/`)

Simulated ECU processes that write sensor values and heartbeats:

| Version | ECU | Behavior |
|---------|-----|----------|
| v1.0 | motor_ecu | Standard mode: RPM 1400–1600, temp 40–49°C, healthy heartbeat |
| v1.1 | motor_ecu_v1.1 | Eco mode: RPM 840–960, temp 35–44°C, healthy heartbeat |
| v1.2 | motor_ecu_v1.2_broken | Erratic sensors, **stops heartbeat after 3 ticks** |
| v1.0 | brake_ecu | Pressure + temperature sensors |
| v1.0 | battery_ecu | SOC + voltage sensors |

v1.2 is **legitimately signed** — the security layer accepts it. The health monitor catches the behavioral failure. These are two independent safety nets.

---

## Code Flow — Step by Step

### Path A: Local Installer (no cloud)

Used by `Scripts/run_demo.sh` when `CLOUD` is not set.

```
run_demo.sh
  │
  ├─ 1. Reset ECU to v1.0 on slotA, start ECU process
  ├─ 2. Package firmware (sign + tarball) via package_generator.py
  │
  ├─ 3. Install v1.1
  │     └─ Installer/installer.py
  │           ├─ Extract motorecu_v1.1.tar.gz
  │           ├─ Verify Ed25519 signature + SHA-256 checksum
  │           ├─ Check downgrade (1.0 → 1.1 OK)
  │           ├─ bootloader stage → writes to slotB (inactive)
  │           ├─ bootloader activate → flips to slotB, restarts ECU
  │           └─ health_monitor --grace --duration 32
  │                 ├─ Reads heartbeat.txt every 1s
  │                 └─ v1.1 is healthy → grace period completes
  │
  ├─ 4. Install v1.2-broken
  │     └─ Same pipeline, but v1.2 stops heartbeat after 3 ticks
  │           ├─ health_monitor detects 3 consecutive failures
  │           └─ Triggers bootloader rollback → back to v1.1 on slotA
  │
  └─ 5. Assert final version is 1.1, print ota.log
```

### Path B: Cloud + Client

Used by `Scripts/run_cloud_demo.sh` (`CLOUD=1`).

```
run_cloud_demo.sh
  │
  ├─ Same reset + packaging as Path A
  ├─ Start uvicorn OTA_Cloud.server:app on port 8080
  │
  └─ OTA_Client/client.py (instead of direct installer)
        ├─ GET /updates/MotorECU
        ├─ GET /packages/MotorECU/1.1  (download)
        └─ Installer/installer.py (same steps as Path A from here)
```

### Path C: Fleet (multi-ECU)

Used by `Scripts/run_fleet_demo.sh`.

```
run_fleet_demo.sh
  │
  ├─ init_ecu.sh all → reset MotorECU, BrakeECU, BatteryECU to v1.0
  ├─ Package v1.1 firmware for all three ECUs
  ├─ Start OTA cloud server
  └─ OTA_Client/fleet.py
        └─ For each ECU: client.run_client() → install v1.1
```

---

## A/B Slot State Machine

```
                    ┌──────────────┐
                    │  Running on  │
                    │   slot A     │
                    │  (v1.0)      │
                    └──────┬───────┘
                           │ stage v1.1
                           ▼
                    ┌──────────────┐
                    │  slot A: v1.0│  ← still running
                    │  slot B: v1.1│  ← staged (inactive)
                    └──────┬───────┘
                           │ activate
                           ▼
                    ┌──────────────┐
                    │  Running on  │
                    │   slot B     │
                    │  (v1.1)      │
                    └──────┬───────┘
                           │ stage v1.2-broken + activate
                           ▼
                    ┌──────────────┐
                    │  Running on  │
                    │   slot A     │  ← was slot B, now flipped
                    │  (v1.2)      │  ← broken, heartbeat fails
                    └──────┬───────┘
                           │ health monitor rollback
                           ▼
                    ┌──────────────┐
                    │  Running on  │
                    │   slot B     │  ← flipped back
                    │  (v1.1)      │  ← restored from previous slot
                    └──────────────┘
```

Key invariant: the running firmware is **never overwritten**. Updates always go to the inactive slot first; activation is a slot flip.

---

## Security Model

Two independent safety layers:

| Layer | What it checks | When | Example |
|-------|----------------|------|---------|
| **Cryptographic** | Ed25519 signature + SHA-256 checksum | Before staging | Tampered package rejected |
| **Version policy** | Downgrade protection | Before staging | v1.1 → v1.0 rejected |
| **Behavioral** | Heartbeat health | After activation (grace period) | v1.2-broken rolled back |

A package can pass security checks but still fail health monitoring — this is intentional and mirrors real-world OTA systems where signed firmware can still be buggy.

---

## Logging

All OTA events append to per-ECU logs:

```
Virtual_ECU/MotorECU/logs/ota.log
```

Components tag their log lines: `[installer]`, `[client]`, `[cloud]`, `[fleet]`, `[health_monitor]`.

Example:

```
[2026-07-25 23:09:59] ERROR  [health_monitor] FAILURE THRESHOLD REACHED — triggering automatic rollback
[2026-07-25 23:10:01] INFO   [client] Update available: 1.1 → 1.2
```

---

## Multi-ECU Support

Three virtual ECUs share the same architecture:

| ECU | Firmware | Sensors |
|-----|----------|---------|
| MotorECU | `Firmware/motor_ecu*` | RPM, temperature |
| BrakeECU | `Firmware/brake_ecu` | Pressure, temperature |
| BatteryECU | `Firmware/battery_ecu` | SOC, voltage |

ECU metadata and path resolution: `Tools/ecu_registry.py`

Bootloader accepts `--ecu MotorECU|BrakeECU|BatteryECU` on every command.

---

## Design Decisions

1. **Bootloader is the sole flash writer** — installer and client never touch slot binaries directly.
2. **Security vs. health are separate** — signed but broken firmware demonstrates real-world failure modes.
3. **A/B slots** — old firmware always remains intact in the other slot for rollback.
4. **No external dependencies for ECU state** — hand-rolled JSON parsing in C for portability.
5. **File-based simulation** — heartbeats, PIDs, and flash are plain files/processes, making the full pipeline observable without hardware.

---

## Related Documentation

- [TESTING.md](./TESTING.md) — how to test the project end to end
- [DEMO_COMMANDS.md](./DEMO_COMMANDS.md) — commands to demonstrate the project to others
- [signing.md](./signing.md) — manifest signing convention
