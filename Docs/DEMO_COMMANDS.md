# SDV OTA Platform — Demo Commands Cheat Sheet

Copy-paste commands for demonstrating this project to others. Organized from "show the whole thing in 60 seconds" to granular step-by-step walkthroughs.

---

## Before You Demo

### One-time setup (Docker)

```bash
cd sdv-ota-platform
docker compose up --build
docker compose run dev bash
```

### One-time setup (native)

```bash
cd sdv-ota-platform
make -C Firmware/motor_ecu rebuild
make -C Firmware/motor_ecu_v1.1 rebuild
make -C Firmware/motor_ecu_v1.2_broken rebuild
make -C Firmware/brake_ecu rebuild
make -C Firmware/battery_ecu rebuild
make -C Bootloader rebuild
make -C Health_Monitor rebuild
python3 Tools/gen_keys.py
```

---

## 60-Second Full Demo (recommended for presentations)

Runs the complete OTA story: v1.0 → v1.1 (success) → v1.2-broken (auto-rollback back to v1.1).

```bash
FAST=1 ./Scripts/run_demo.sh
```

**Talk track while it runs:**

1. "We start on firmware v1.0, running on slot A."
2. "A signed v1.1 update is staged to slot B, activated, and watched for 32 seconds."
3. "v1.1 passes the health check — eco mode, healthy heartbeat."
4. "Now we push v1.2 — it's legitimately signed, but behaviorally broken."
5. "The health monitor detects 3 consecutive heartbeat failures and rolls back automatically."
6. "Final state: still on v1.1. No human intervention."

**Expected final output:**

```
ASSERT PASSED: final version is 1.1
Demo complete (XXs)
```

---

## Cloud Path Demo (~60 seconds)

Same story, but updates flow through a FastAPI server and OTA client — closer to a real vehicle architecture.

```bash
./Scripts/run_cloud_demo.sh
```

**Talk track addition:** "The vehicle polls an OTA cloud server over HTTP, downloads the signed package, verifies it locally, then installs."

---

## Fleet Demo (~60 seconds)

Shows multi-ECU updates across MotorECU, BrakeECU, and BatteryECU.

```bash
FAST=1 ./Scripts/run_fleet_demo.sh
```

**Talk track:** "A single fleet orchestrator updates three ECUs — motor, brake, and battery — all via the same signed OTA pipeline."

Verify after:

```bash
./Bootloader/build/bootloader --ecu MotorECU status
./Bootloader/build/bootloader --ecu BrakeECU status
./Bootloader/build/bootloader --ecu BatteryECU status
```

---

## Security Tests (~10 seconds)

Demonstrate tamper rejection and downgrade protection:

```bash
python3 Tests/test_signing.py && \
python3 Tests/test_tamper.py && \
python3 Tests/test_downgrade.py
```

**Talk track:** "Before any firmware reaches flash, we verify Ed25519 signatures and SHA-256 checksums. Tampered packages are rejected. Downgrades are blocked."

---

## Step-by-Step Live Walkthrough

Use this when you want to explain each layer individually.

### Step 1: Show initial ECU state

```bash
./Bootloader/build/bootloader status
```

Expected: version 1.0, active slot A.

### Step 2: Show the running ECU heartbeat

```bash
cat Virtual_ECU/MotorECU/runtime/heartbeat.txt
sleep 2
cat Virtual_ECU/MotorECU/runtime/heartbeat.txt
```

The timestamp should advance — the ECU is alive.

### Step 3: Package signed firmware

```bash
python3 Scripts/package_generator.py \
  Firmware/motor_ecu_v1.1/build/motor_ecu \
  --version 1.1 --ecu MotorECU --out packages/

ls -la packages/motorecu_v1.1.tar.gz
tar -tzf packages/motorecu_v1.1.tar.gz
```

Shows `firmware.bin` + `manifest.json` inside the signed tarball.

### Step 4: Install with verification + activation

```bash
python3 Installer/installer.py packages/motorecu_v1.1.tar.gz \
  --activate --grace-duration 32
```

Watch for: signature verify → checksum verify → stage → activate → grace period → healthy.

### Step 5: Confirm v1.1 is running

```bash
./Bootloader/build/bootloader status
```

Expected: version 1.1, active slot B.

### Step 6: Install broken v1.2 (watch rollback happen)

```bash
python3 Scripts/package_generator.py \
  Firmware/motor_ecu_v1.2_broken/build/motor_ecu \
  --version 1.2 --ecu MotorECU --out packages/

python3 Installer/installer.py packages/motorecu_v1.2.tar.gz \
  --activate --grace-duration 12
```

Watch for: health monitor failure threshold → automatic rollback.

### Step 7: Show final state and logs

```bash
./Bootloader/build/bootloader status
cat Virtual_ECU/MotorECU/logs/ota.log
```

Expected: version 1.1 restored after rollback.

---

## Cloud Server Demo (two-terminal setup)

### Terminal 1 — Start the OTA server

```bash
pip install -r OTA_Cloud/requirements.txt
uvicorn OTA_Cloud.server:app --host 0.0.0.0 --port 8080
```

### Terminal 2 — Interact with the API

```bash
# Health check
curl http://localhost:8080/health

# See available updates for MotorECU
curl http://localhost:8080/updates/MotorECU | python3 -m json.tool

# Full catalog
curl http://localhost:8080/catalog | python3 -m json.tool

# Download a package
curl -O http://localhost:8080/packages/MotorECU/1.1
```

### Terminal 2 — Run the OTA client

```bash
python3 OTA_Client/client.py \
  --server http://localhost:8080 \
  --ecu MotorECU --version 1.1 \
  --activate --grace-duration 32
```

---

## Docker Demo Commands

```bash
# Build everything
docker compose up --build

# Interactive shell with repo mounted
docker compose run dev bash

# Inside container — run any demo
FAST=1 ./Scripts/run_demo.sh

# Run OTA server (accessible on host at localhost:8080)
docker compose up ota_server
```

From the host machine:

```bash
curl http://localhost:8080/health
```

---

## Recording a Demo Video

```bash
# Fast timed demo
FAST=1 ./Scripts/record_demo.sh

# With asciinema cast file output
RECORD=1 ./Scripts/record_demo.sh
# Creates demo.cast — play with: asciinema play demo.cast
```

---

## Useful Inspection Commands (during Q&A)

```bash
# ECU version and slot state
./Bootloader/build/bootloader status
./Bootloader/build/bootloader --ecu BrakeECU status

# OTA event log
cat Virtual_ECU/MotorECU/logs/ota.log

# Version config file
cat Virtual_ECU/MotorECU/config/version.json

# Live heartbeat
cat Virtual_ECU/MotorECU/runtime/heartbeat.txt

# List signed packages
ls packages/

# Inspect a manifest without extracting
tar -xOf packages/motorecu_v1.1.tar.gz manifest.json | python3 -m json.tool

# Show public key (safe to share)
cat Tools/keys/ota_public_key.pem
```

---

## Environment Variables

Tune demo behavior without editing scripts:

| Variable | Default | Effect |
|----------|---------|--------|
| `FAST=1` | `0` | Skip rebuild (~60s demos) |
| `CLOUD=1` | `0` | Use FastAPI server + OTA client |
| `SERVER_URL` | `http://localhost:8080` | OTA server URL |
| `GRACE_V11` | `32` | Grace period for v1.1 install (seconds) |
| `GRACE_V12` | `12` | Grace period for v1.2 install (seconds) |
| `GRACE` | `15` | Fleet demo grace duration |
| `RECORD=1` | `0` | Save asciinema recording |

Examples:

```bash
FAST=1 CLOUD=1 ./Scripts/run_demo.sh
GRACE_V11=20 GRACE_V12=8 FAST=1 ./Scripts/run_demo.sh
```

---

## Suggested Demo Order for an Audience

| Order | Command | Duration | What it shows |
|-------|---------|----------|---------------|
| 1 | Security tests | ~10s | Signing, tamper, downgrade protection |
| 2 | `FAST=1 ./Scripts/run_demo.sh` | ~60s | Full OTA + rollback story |
| 3 | `./Scripts/run_cloud_demo.sh` | ~60s | Cloud server + client path |
| 4 | `FAST=1 ./Scripts/run_fleet_demo.sh` | ~60s | Multi-ECU fleet update |
| 5 | `cat Virtual_ECU/MotorECU/logs/ota.log` | instant | Audit trail |

Total presentation time: ~3–4 minutes for all four demos, plus Q&A.

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system design and code flow
- [TESTING.md](./TESTING.md) — detailed testing guide
- [signing.md](./signing.md) — manifest signing convention
