# SDV OTA Platform — End-to-End Testing Guide

This document describes how to test every feature in the project: unit/security tests, full OTA demos, cloud path, fleet updates, and manual spot checks.

---

## Prerequisites

### Option A: Docker (recommended)

```bash
docker compose up --build
docker compose run dev bash
```

All commands below assume you are inside the dev container (or at the repo root with native tooling).

### Option B: Native / WSL

Install:

- `gcc`, `make`, `python3`, `pip`
- Python packages: `cryptography`, `fastapi`, `uvicorn[standard]`

Build all components:

```bash
make -C Firmware/motor_ecu rebuild
make -C Firmware/motor_ecu_v1.1 rebuild
make -C Firmware/motor_ecu_v1.2_broken rebuild
make -C Firmware/brake_ecu rebuild
make -C Firmware/battery_ecu rebuild
make -C Bootloader rebuild
make -C Health_Monitor rebuild
python3 Tools/gen_keys.py   # first time only
```

Demo scripts auto-generate signing keys if missing.

---

## Test Layers Overview

| Layer | What it validates | How long |
|-------|-------------------|----------|
| Unit / security tests | Signing, tamper rejection, downgrade blocking | ~10s |
| Full OTA demo (local) | Happy path + auto-rollback | ~60–90s |
| Cloud path demo | Same via FastAPI + OTA client | ~60–90s |
| Fleet demo | Multi-ECU update (3 ECUs) | ~60–120s |
| Manual spot checks | Individual components | ad hoc |

---

## 1. Security & Unit Tests

Run from repo root:

```bash
python3 Tests/test_signing.py
python3 Tests/test_tamper.py
python3 Tests/test_downgrade.py
```

Or all at once:

```bash
python3 Tests/test_signing.py && \
python3 Tests/test_tamper.py && \
python3 Tests/test_downgrade.py
```

### What each test covers

| Test | Validates | Expected output |
|------|-----------|-----------------|
| `test_signing.py` | Ed25519 key generation, sign, verify round-trip | `PASS` / `All signing tests passed.` |
| `test_tamper.py` | Tampered checksum rejected; corrupted binary rejected by installer | `PASS` / `All tamper tests passed.` |
| `test_downgrade.py` | Installer blocks v1.1 → v1.0 downgrade attempt | `PASS` / `All downgrade tests passed.` |

### Additional tests in Tools/

```bash
python3 Tools/test_signing.py
python3 Tools/test_packaging.py
python3 Tools/test_installer_rejects_tampered.py
```

### C unit test (manual compile)

```bash
gcc -o /tmp/test_version_store Tests/test_version_store.c Common/version_store/version_store.c -I Common/version_store
/tmp/test_version_store
```

---

## 2. Full OTA Demo — Happy Path + Rollback

This is the primary end-to-end validation. It exercises the complete pipeline:

1. Reset to v1.0
2. Install v1.1 (signed, healthy) → survives grace period
3. Install v1.2-broken (signed, unhealthy) → auto-rollback to v1.1

```bash
FAST=1 ./Scripts/run_demo.sh
```

Use `FAST=1` to skip rebuild (~60s). Omit it for a full rebuild (~2–3 min).

### Expected outcome

**Final state:**

```
version      : 1.1
active_slot  : B (or A, depending on rollback path)
pending_slot : null
```

**Console:**

```
ASSERT PASSED: final version is 1.1
Demo complete (XXs)
```

**Log file** (`Virtual_ECU/MotorECU/logs/ota.log`) should contain:

- `[installer]` verification passed for v1.1
- `[installer]` verification passed for v1.2
- `[health_monitor]` FAILURE THRESHOLD REACHED — triggering automatic rollback
- Bootloader rollback messages

### What this proves

| Scenario | Result |
|----------|--------|
| Signed update v1.0 → v1.1 | Staged, activated, survives grace period |
| Broken update v1.1 → v1.2 | Signed package accepted, health check fails, **auto-rollback to v1.1** |

---

## 3. Cloud Path Demo

Same scenarios as the full demo, but updates go through the FastAPI server and OTA client instead of calling the installer directly.

```bash
./Scripts/run_cloud_demo.sh
```

This sets `CLOUD=1` and `FAST=1` internally, then runs `run_demo.sh`.

### What this adds to the test

- OTA cloud server starts on port 8080
- Client polls `GET /updates/MotorECU`
- Client downloads `GET /packages/MotorECU/{version}`
- Installer is still called locally after download

### Verify cloud server independently

In one terminal:

```bash
pip install -r OTA_Cloud/requirements.txt
uvicorn OTA_Cloud.server:app --host 0.0.0.0 --port 8080
```

In another terminal (after packaging firmware):

```bash
curl http://localhost:8080/health
curl http://localhost:8080/updates/MotorECU
curl http://localhost:8080/catalog
```

---

## 4. Multi-ECU Fleet Demo

Tests updating MotorECU, BrakeECU, and BatteryECU in one run.

```bash
FAST=1 ./Scripts/run_fleet_demo.sh
```

### What it does

1. `init_ecu.sh all` — reset all 3 ECUs to v1.0
2. Package v1.1 firmware for each ECU
3. Start OTA cloud server
4. `OTA_Client/fleet.py` — update all ECUs to v1.1

### Expected outcome

All three ECUs reach version 1.1:

```bash
./Bootloader/build/bootloader --ecu MotorECU status
./Bootloader/build/bootloader --ecu BrakeECU status
./Bootloader/build/bootloader --ecu BatteryECU status
```

Each should show `current_version: 1.1`.

---

## 5. Manual Component Tests

### Bootloader

```bash
# Check status
./Bootloader/build/bootloader status
./Bootloader/build/bootloader --ecu BrakeECU status

# Manual stage + activate
./Bootloader/build/bootloader stage Firmware/motor_ecu_v1.1/build/motor_ecu
./Bootloader/build/bootloader activate

# Manual rollback
./Bootloader/build/bootloader rollback
```

### Package generation

```bash
python3 Scripts/package_generator.py \
  Firmware/motor_ecu_v1.1/build/motor_ecu \
  --version 1.1 --ecu MotorECU --out packages/
```

Verify the package exists:

```bash
ls packages/motorecu_v1.1.tar.gz
tar -tzf packages/motorecu_v1.1.tar.gz
# Expected: firmware.bin, manifest.json
```

### Direct installer (no cloud)

```bash
python3 Installer/installer.py packages/motorecu_v1.1.tar.gz \
  --activate --grace-duration 32
```

### OTA client (with server running)

```bash
python3 OTA_Client/client.py \
  --server http://localhost:8080 \
  --ecu MotorECU --version 1.1 \
  --activate --grace-duration 32
```

### Fleet orchestrator (with server running)

```bash
python3 OTA_Client/fleet.py \
  --server http://localhost:8080 \
  --ecus MotorECU,BrakeECU,BatteryECU \
  --version 1.1 --activate --grace-duration 15
```

### ECU initialization

```bash
./Scripts/init_ecu.sh all          # all ECUs
./Scripts/init_ecu.sh MotorECU       # single ECU
```

### ECU process control

```bash
./Scripts/start_motor_ecu.sh
./Scripts/status_motor_ecu.sh
./Scripts/stop_motor_ecu.sh
```

---

## 6. Tamper & Downgrade Scenarios (Manual)

### Tamper rejection

Security tests cover this automatically. To observe manually:

1. Build a valid package
2. Modify a byte inside the tarball
3. Run installer — expect `REJECTED: manifest signature invalid` or `checksum mismatch`

### Downgrade rejection

1. Ensure ECU is on v1.1 (run demo or install v1.1)
2. Attempt to install v1.0:

```bash
python3 Installer/installer.py packages/motorecu_v1.0.tar.gz
```

Expected: `REJECTED: downgrade not allowed (1.1 -> 1.0)`

---

## 7. Observability Checks

After any demo or manual test, inspect these files:

```bash
# Structured OTA log
cat Virtual_ECU/MotorECU/logs/ota.log

# ECU version state
cat Virtual_ECU/MotorECU/config/version.json

# Live heartbeat (should update every ~1s while ECU is running)
watch -n1 cat Virtual_ECU/MotorECU/runtime/heartbeat.txt

# Running ECU PID
cat Virtual_ECU/MotorECU/runtime/ecu.pid
```

---

## 8. Docker-Specific Testing

```bash
# Build image and show status
docker compose up --build

# Interactive dev shell
docker compose run dev bash

# Run OTA server (exposed on host port 8080)
docker compose up ota_server

# From host machine (with ota_server running):
curl http://localhost:8080/health
```

Inside the dev container, all demo and test commands work the same as native.

---

## 9. Demo Recording (Optional)

For a timed, presentation-ready run:

```bash
FAST=1 ./Scripts/record_demo.sh
```

With asciinema recording:

```bash
RECORD=1 ./Scripts/record_demo.sh
# Output: demo.cast
```

---

## Test Matrix — Quick Reference

| Test | Command | Pass criteria |
|------|---------|---------------|
| Signing | `python3 Tests/test_signing.py` | All tests passed |
| Tamper | `python3 Tests/test_tamper.py` | All tests passed |
| Downgrade | `python3 Tests/test_downgrade.py` | All tests passed |
| Full OTA | `FAST=1 ./Scripts/run_demo.sh` | Final version 1.1, rollback logged |
| Cloud OTA | `./Scripts/run_cloud_demo.sh` | Same as full OTA |
| Fleet | `FAST=1 ./Scripts/run_fleet_demo.sh` | All 3 ECUs at v1.1 |
| Server health | `curl localhost:8080/health` | `{"status":"ok",...}` |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| `bootloader: not found` | C components not built | `make -C Bootloader rebuild` |
| `REJECTED: manifest signature invalid` | Keys mismatch or tampered package | `python3 Tools/gen_keys.py` and re-package |
| `Cannot reach OTA server` | Server not running | Start uvicorn or use `run_cloud_demo.sh` |
| Demo hangs on grace period | Normal — waits for health monitor | v1.1 grace ~32s, v1.2 grace ~12s |
| `SKIP: binary not built` in tests | Firmware not compiled | Run `make -C Firmware/motor_ecu_v1.1 rebuild` |
| Port 8080 in use | Another process on 8080 | `kill $(lsof -t -i:8080)` or change `SERVER_URL` |

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system design and code flow
- [DEMO_COMMANDS.md](./DEMO_COMMANDS.md) — commands for live demonstrations
- [signing.md](./signing.md) — manifest signing convention
