# SDV OTA Platform

A simulated Over-The-Air (OTA) update system for automotive ECUs with **A/B slot architecture**, **Ed25519-signed firmware delivery**, and **automatic health-checked rollback** — no hardware required.

> *"Remote firmware deployment with cryptographic verification and zero-touch rollback, built entirely in software."*

---

## What It Proves

| Scenario | Result |
|----------|--------|
| Signed update v1.0 → v1.1 | Staged, activated, survives 30s grace period |
| Broken update v1.1 → v1.2 | Signed package accepted, health check fails, **auto-rollback to v1.1** |
| Tampered package | Rejected before reaching flash |
| Downgrade attempt | Rejected before staging |

---

## Architecture

```
OTA_Cloud (FastAPI)          ← serves signed packages from packages/
    ↓
OTA_Client (Python)          ← poll, download, verify signature + checksum
    ↓
Installer (Python)           ← extract, verify, call bootloader
    ↓
Bootloader (C)               ← ONLY component that writes flash slots
    ↓
Virtual_ECU (C)              ← slotA / slotB A/B firmware images
    ↓ heartbeat every 1s
Health_Monitor (C)           ← grace-period watch → auto rollback
```

**Key design decisions:**

- **A/B slots** — never overwrite running firmware; new update goes to inactive slot first
- **Ed25519 signing** — checksum = integrity, signature = authenticity; both required
- **Grace-period rollback** — 3 consecutive heartbeat failures within the watch window triggers `bootloader rollback` with zero human input

---

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
docker compose run dev bash
./Scripts/run_demo.sh
```

### Native / WSL

```bash
# Build
make -C Firmware/motor_ecu rebuild
make -C Firmware/motor_ecu_v1.1 rebuild
make -C Firmware/motor_ecu_v1.2_broken rebuild
make -C Bootloader rebuild
make -C Health_Monitor rebuild

python3 Tools/gen_keys.py   # first time only

# Full demo (~60s without rebuild)
FAST=1 ./Scripts/run_demo.sh
```

---

## Demo Scripts

| Script | Purpose |
|--------|---------|
| `./Scripts/run_demo.sh` | Full OTA happy path + rollback (local installer) |
| `FAST=1 ./Scripts/run_demo.sh` | Skip rebuild — ~60s, suitable for recording |
| `./Scripts/run_cloud_demo.sh` | Same demo via FastAPI server + OTA client |
| `./Scripts/record_demo.sh` | Timed fast demo; `RECORD=1` saves `demo.cast` |

**Expected final state after demo:**

```
version      : 1.1
active_slot  : B
pending_slot : null
```

---

## OTA Cloud Server (Phase 13)

```bash
pip install -r OTA_Cloud/requirements.txt
python3 Scripts/package_generator.py Firmware/motor_ecu_v1.1/build/motor_ecu --version 1.1 --ecu MotorECU --out packages/
uvicorn OTA_Cloud.server:app --host 0.0.0.0 --port 8080
```

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Server health check |
| `GET /updates/{ecu}` | Latest + all available packages |
| `GET /packages/{ecu}/{version}` | Download signed `.tar.gz` |

---

## OTA Client (Phase 14)

```bash
python3 OTA_Client/client.py --server http://localhost:8080 --ecu MotorECU --activate --grace-duration 32
python3 OTA_Client/client.py --server http://localhost:8080 --ecu MotorECU --version 1.1 --activate
```

Flow: poll server → compare versions → download → verify Ed25519 + SHA-256 → call Installer.

---

## Bootloader CLI

Run from **repo root**:

```bash
./Bootloader/build/bootloader status
./Bootloader/build/bootloader stage <firmware_path>
./Bootloader/build/bootloader activate
./Bootloader/build/bootloader rollback
```

---

## Firmware Versions

| Version | Mode | RPM | TEMP | Heartbeat | Health |
|---------|------|-----|------|-----------|--------|
| v1.0 | Standard | 1400–1600 | 40–49°C | Continuous | PASS |
| v1.1 | Eco Mode | 840–960 | 35–44°C | Continuous | PASS |
| v1.2 | BROKEN | 0 or 3000 | 120°C | Stops after 3 ticks | FAIL → rollback |

v1.2 is **legitimately signed** — security layer accepts it. Health monitor catches the behavioral failure. Two independent safety nets.

---

## Security

- **Algorithm:** Ed25519 (`Tools/keys/ota_signing_key.pem` — gitignored)
- **Manifest fields:** `version`, `ecu`, `size`, `checksum`, `signature`
- **Downgrade protection:** Installer rejects `current > new` before staging
- **Tamper rejection:** Invalid signature or checksum mismatch → refuse install

### Run tests

```bash
python3 Tests/test_signing.py
python3 Tests/test_tamper.py
python3 Tests/test_downgrade.py
```

---

## Logging

All OTA events append to `Virtual_ECU/MotorECU/logs/ota.log`:

```
[2026-07-25 23:09:59] ERROR  [health_monitor] FAILURE THRESHOLD REACHED — triggering automatic rollback
[2026-07-25 23:10:01] INFO   [client] Update available: 1.1 → 1.2
```

Components: `[installer]`, `[client]`, `[cloud]`, health monitor (C), bootloader (stdout).

---

## Project Structure

```
sdv-ota-platform/
├── Bootloader/          # stage / activate / rollback (C)
├── Common/version_store/# version.json read/write API
├── Firmware/            # motor_ecu v1.0, v1.1, v1.2_broken
├── Health_Monitor/      # heartbeat watch + auto rollback
├── OTA_Cloud/           # FastAPI server
├── OTA_Client/          # polling download client
├── Installer/           # verify + stage + activate
├── Scripts/             # demo, packaging, ECU control
├── Tests/               # signing, tamper, downgrade tests
├── Tools/               # keys, signing, shared logging
└── Virtual_ECU/         # flash slots, runtime, config, logs
```

---

## Interview Talking Points

**"How do you know the update is genuine?"**
> Ed25519 signing. Every package has a SHA-256 checksum and an Ed25519 signature. The client verifies the signature against the stored public key before doing anything. Checksum = integrity. Signature = authenticity. You need both.

**"What happens if a bad update is deployed?"**
> The Health Monitor watches the ECU heartbeat for a configurable grace period after activation. Three consecutive failures trigger automatic `bootloader rollback` — the system flips back to the previous slot and restarts the ECU. Zero manual steps.

**"Why A/B slots?"**
> You never overwrite running firmware. The new update goes into the inactive slot first. Only after the health check confirms stability does the system commit. The old firmware is always intact in the other slot.

---

## Resume Bullets (Phase 21)

- Built a virtual ECU OTA platform with A/B slot bootloader, Ed25519-signed packages, and automatic health-checked rollback — full pipeline from cloud server to flash, no hardware required
- Implemented downgrade protection and tamper rejection (signature + checksum verification) before firmware reaches flash slots
- Designed grace-period health monitoring with consecutive-failure threshold triggering zero-touch rollback, mirroring production automotive OTA safety patterns

---

## License

Educational / portfolio project.
