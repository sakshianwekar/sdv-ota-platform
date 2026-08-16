# SDV OTA Platform — End-to-End Testing Guide

This document describes how to test every feature in the project: unit/security tests, full OTA demos, cloud path, fleet updates, and manual spot checks.

Each section includes **what the test does** alongside the commands, so you can follow the flow and know what to expect at each step.

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

Run tests in this order for a full validation pass:

| Layer | What it validates | What you'll see | How long |
|-------|-------------------|-----------------|----------|
| Unit / security tests | Signing, tamper rejection, downgrade blocking | `PASS` messages per test | ~10s |
| Full OTA demo (local) | Happy path + auto-rollback via direct installer | Step banners, grace period waits, `ASSERT PASSED` | ~60–90s |
| Cloud path demo | Same flow via FastAPI server + OTA client | Server startup, HTTP download, same rollback | ~60–90s |
| Fleet demo | Multi-ECU update (3 ECUs) | Per-ECU install progress, 3 status outputs | ~60–120s |
| Manual spot checks | Individual components in isolation | Component-specific output | ad hoc |

---

## 1. Security & Unit Tests

These tests validate the **security layer** in isolation — before running any full OTA demo. They confirm that packages are signed correctly, tampered firmware is rejected, and version downgrades are blocked.

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

### What each test does

#### `test_signing.py` — manifest signing & verification

**Purpose:** Confirms the Ed25519 signing pipeline works end-to-end.

**Flow while it runs:**

1. Loads the OTA signing key pair from `Tools/keys/`
2. Builds a signed manifest for the v1.1 MotorECU firmware binary
3. Verifies that a valid manifest passes both signature and checksum checks
4. Tamper-tests the manifest by changing the checksum → expects signature verification to **fail**
5. Tamper-tests the manifest by corrupting the signature bytes → expects verification to **fail**

**Pass criteria:** `All signing/verification tests passed.`

---

#### `test_tamper.py` — tampered package rejection

**Purpose:** Confirms the installer refuses firmware that has been modified after signing.

**Flow while it runs:**

1. Builds a valid signed manifest for v1.1 firmware
2. Verifies that a tampered checksum in the manifest fails signature check
3. Packages firmware + manifest into a `.tar.gz`
4. Flips one byte inside `firmware.bin` (simulating corruption in transit)
5. Calls `install_package()` on the tampered tarball → expects a `ValueError` mentioning `checksum` or `signature`

**Pass criteria:** `PASS: tampered package correctly rejected` followed by `All tamper rejection tests passed.`

---

#### `test_downgrade.py` — downgrade protection

**Purpose:** Confirms the installer will not allow installing an older firmware version over a newer one.

**Flow while it runs:**

1. **Unit checks:** Tests `compare_versions()` and `is_downgrade()` logic (`1.0 < 1.1`, `1.2 > 1.1`, downgrade `1.1 → 1.0` is blocked)
2. **Integration check** (if `packages/motorecu_v1.0.tar.gz` exists):
   - Temporarily sets `version.json` to `current_version: 1.1`
   - Attempts to install the v1.0 package
   - Expects `REJECTED: downgrade not allowed`
   - Restores the original `version.json`

**Pass criteria:** `PASS: downgrade correctly rejected` (or `SKIP` if v1.0 package missing) followed by `All downgrade protection tests passed.`

---

### Summary table

| Test | What it validates | Expected output |
|------|-------------------|-----------------|
| `test_signing.py` | Ed25519 sign/verify round-trip; tampered manifest detection | `All signing/verification tests passed.` |
| `test_tamper.py` | Corrupted firmware binary rejected by installer | `All tamper rejection tests passed.` |
| `test_downgrade.py` | Version comparison logic + installer blocks downgrade | `All downgrade protection tests passed.` |

### Additional tests in Tools/

```bash
python3 Tools/test_signing.py
python3 Tools/test_packaging.py
python3 Tools/test_installer_rejects_tampered.py
```

| Test | What it does |
|------|--------------|
| `Tools/test_signing.py` | Same signing/verification checks as `Tests/test_signing.py`, run from the Tools directory |
| `Tools/test_packaging.py` | Packages v1.1 firmware into a tarball, extracts it, and verifies signature + checksum on the unpacked contents |
| `Tools/test_installer_rejects_tampered.py` | Builds a tampered tarball (flipped firmware byte) and confirms the installer raises `ValueError` |

### C unit test (manual compile)

Tests the C `version_store` module — reads/writes `version.json`, slot tracking, and pending version state.

```bash
gcc -o /tmp/test_version_store Tests/test_version_store.c Common/version_store/version_store.c -I Common/version_store
/tmp/test_version_store
```

**What it does:** Compiles and runs self-contained assertions against `version_store.c` (no Python test framework). Prints `PASS` / `FAIL` per assertion; exits 0 if all pass.

---

## 2. Full OTA Demo — Happy Path + Rollback

This is the **primary end-to-end validation**. It exercises the complete OTA pipeline in one scripted run: a successful update followed by a broken update that triggers automatic rollback.

```bash
FAST=1 ./Scripts/run_demo.sh
```

Use `FAST=1` to skip rebuild (~60s). Omit it for a full rebuild (~2–3 min).

### Step-by-step flow (what happens while it runs)

| Step | What happens | What to watch for |
|------|--------------|-------------------|
| **Setup** | Generates signing keys if missing; optionally rebuilds all firmware + bootloader + health monitor | `FAST=1` prints `skipping rebuild` |
| **Step 1 — Reset to v1.0** | Stops any running ECU process; copies v1.0 binary to both flash slots A and B; resets `version.json` to `1.0` on slot A; starts the v1.0 ECU process | `Reset complete — running v1.0 on slotA` |
| **Package** | Creates signed `.tar.gz` packages for v1.0, v1.1, and v1.2-broken | Packages written to `packages/` |
| **Step 2 — Bootloader status** | Prints current version, active slot, and pending slot | `current_version: 1.0`, `active_slot: A` |
| **Step 3 — Install v1.1** | Installer verifies signature + checksum → bootloader stages v1.1 to inactive slot B → activates slot B → health monitor watches for ~32s grace period | v1.1 ECU starts in eco mode; heartbeat stays healthy |
| **Step 4 — Confirm v1.1 healthy** | Prints bootloader status after grace period | `current_version: 1.1`, `active_slot: B`, `pending_slot: null` |
| **Step 5 — Install v1.2-broken** | Same install flow for v1.2 (signed but behaviorally broken) → health monitor detects 3 consecutive heartbeat failures → triggers automatic rollback to v1.1 | Rollback messages in console and `ota.log` |
| **Step 6 — Final state** | Prints bootloader status and asserts version is still 1.1 | `ASSERT PASSED: final version is 1.1` |
| **Step 7 — OTA log** | Dumps the full structured log from `Virtual_ECU/MotorECU/logs/ota.log` | Installer, bootloader, and health monitor entries |

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

Same scenarios as the full demo (v1.0 → v1.1 success → v1.2-broken rollback), but updates go through the **FastAPI OTA server** and **OTA client** instead of calling the installer directly. This mirrors a real vehicle architecture where the ECU polls a cloud server for updates.

```bash
./Scripts/run_cloud_demo.sh
```

This sets `CLOUD=1` and `FAST=1` internally, then runs `run_demo.sh`.

### What changes vs. the local demo

| Component | Local demo (`run_demo.sh`) | Cloud demo (`run_cloud_demo.sh`) |
|-----------|--------------------------|----------------------------------|
| Package delivery | Installer reads local `.tar.gz` directly | OTA client polls server, downloads package |
| Server | Not used | FastAPI server on port 8080 |
| Install step | `Installer/installer.py` called directly | Client downloads, then calls installer locally |

### Step-by-step flow (cloud-specific steps)

| Step | What happens |
|------|--------------|
| **Start OTA server** | `uvicorn` launches `OTA_Cloud/server:app` on `127.0.0.1:8080`; script waits until `/health` responds |
| **Install v1.1** | Client calls `GET /updates/MotorECU` → downloads `GET /packages/MotorECU/1.1` → verifies + installs locally |
| **Install v1.2** | Same cloud download path for v1.2; rollback behavior is identical to local demo |
| **Stop OTA server** | Server process killed on script exit (via trap) |

### Verify cloud server independently

In one terminal:

```bash
pip install -r OTA_Cloud/requirements.txt
uvicorn OTA_Cloud.server:app --host 0.0.0.0 --port 8080
```

In another terminal (after packaging firmware):

```bash
curl http://localhost:8080/health      # Server is up — returns {"status":"ok",...}
curl http://localhost:8080/updates/MotorECU   # Lists available updates for MotorECU
curl http://localhost:8080/catalog       # Full package catalog across all ECUs
```

| Endpoint | What it does |
|----------|--------------|
| `GET /health` | Liveness check — confirms server is running |
| `GET /updates/{ecu}` | Returns available firmware versions for a given ECU |
| `GET /catalog` | Returns all packaged firmware across all ECUs |

---

## 4. Multi-ECU Fleet Demo

Tests updating **MotorECU, BrakeECU, and BatteryECU** in a single orchestrated run — simulating a fleet-wide OTA campaign.

```bash
FAST=1 ./Scripts/run_fleet_demo.sh
```

### Step-by-step flow (what happens while it runs)

| Step | What happens | What to watch for |
|------|--------------|-------------------|
| **Step 1 — Initialize all ECUs** | `init_ecu.sh all` resets all 3 virtual ECUs to v1.0 on slot A, clears logs and runtime state | Three ECU directories under `Virtual_ECU/` reset |
| **Step 2 — Package firmware** | Creates signed v1.1 packages for MotorECU, BrakeECU, and BatteryECU | `packages/motorecu_v1.1.tar.gz`, `brakeecu_v1.1.tar.gz`, `batteryecu_v1.1.tar.gz` |
| **Step 3 — Start OTA server** | Launches FastAPI server on port 8080 | `OTA server ready (PID ...)` |
| **Step 4 — Fleet update** | `OTA_Client/fleet.py` iterates over all 3 ECUs: polls server → downloads package → installs → activates → grace period (~15s each) | Per-ECU install progress in console |
| **Step 5 — Final status** | Prints bootloader status for each ECU | All three show `current_version: 1.1` |

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

Use these commands to test individual components in isolation — useful when debugging a specific layer of the stack.

### Bootloader

Manages A/B flash slots: staging firmware, activating a slot, and rolling back on failure.

```bash
# Check status — shows current version, active slot, pending slot
./Bootloader/build/bootloader status
./Bootloader/build/bootloader --ecu BrakeECU status

# Manual stage + activate — copy firmware to inactive slot, then switch to it
./Bootloader/build/bootloader stage Firmware/motor_ecu_v1.1/build/motor_ecu
./Bootloader/build/bootloader activate

# Manual rollback — revert to the previous slot after a failed update
./Bootloader/build/bootloader rollback
```

| Command | What it does |
|---------|--------------|
| `status` | Reads `version.json` and prints current version, active/pending slots |
| `stage <binary>` | Copies firmware binary to the inactive flash slot |
| `activate` | Switches the active slot to the staged (pending) slot |
| `rollback` | Reverts to the previous slot and version |

### Package generation

Creates a signed `.tar.gz` OTA package from a compiled firmware binary.

```bash
python3 Scripts/package_generator.py \
  Firmware/motor_ecu_v1.1/build/motor_ecu \
  --version 1.1 --ecu MotorECU --out packages/
```

**What it does:** Computes SHA-256 checksum, builds `manifest.json`, signs it with Ed25519, and bundles `firmware.bin` + `manifest.json` into a tarball.

Verify the package exists:

```bash
ls packages/motorecu_v1.1.tar.gz
tar -tzf packages/motorecu_v1.1.tar.gz
# Expected: firmware.bin, manifest.json
```

### Direct installer (no cloud)

Installs a package locally — verifies signature, stages firmware, optionally activates and runs grace period.

```bash
python3 Installer/installer.py packages/motorecu_v1.1.tar.gz \
  --activate --grace-duration 32
```

**What it does:** Full install pipeline without any network: verify → stage → activate → health monitor grace period (32s).

### OTA client (with server running)

Downloads a package from the OTA server, then runs the same local install pipeline.

```bash
python3 OTA_Client/client.py \
  --server http://localhost:8080 \
  --ecu MotorECU --version 1.1 \
  --activate --grace-duration 32
```

**What it does:** Polls `GET /updates/MotorECU`, downloads the signed package, verifies locally, then calls the installer.

### Fleet orchestrator (with server running)

Updates multiple ECUs in sequence via the cloud server.

```bash
python3 OTA_Client/fleet.py \
  --server http://localhost:8080 \
  --ecus MotorECU,BrakeECU,BatteryECU \
  --version 1.1 --activate --grace-duration 15
```

**What it does:** Loops over each ECU in the list, calling the OTA client for each one — same as Step 4 in the fleet demo.

### ECU initialization

Resets a virtual ECU to a clean v1.0 state (both slots, version.json, logs).

```bash
./Scripts/init_ecu.sh all          # all ECUs
./Scripts/init_ecu.sh MotorECU       # single ECU
```

**What it does:** Stops running ECU process, copies v1.0 binary to both flash slots, resets `version.json`, clears logs and runtime files.

### ECU process control

Start, check, and stop the virtual ECU firmware process.

```bash
./Scripts/start_motor_ecu.sh    # Launch v1.0 ECU binary from active slot
./Scripts/status_motor_ecu.sh   # Show PID, heartbeat age, version
./Scripts/stop_motor_ecu.sh     # Kill ECU process
```

| Script | What it does |
|--------|--------------|
| `start_motor_ecu.sh` | Runs the firmware binary from the active flash slot in the background |
| `status_motor_ecu.sh` | Reads `ecu.pid` and `heartbeat.txt` to show if ECU is alive |
| `stop_motor_ecu.sh` | Sends SIGTERM to the ECU process |

---

## 6. Tamper & Downgrade Scenarios (Manual)

These mirror what the automated security tests do, but let you observe the rejection messages firsthand.

### Tamper rejection

**What you're testing:** The installer must refuse any package where the firmware bytes don't match the signed checksum.

Security tests cover this automatically. To observe manually:

1. **Build a valid package** — creates a correctly signed tarball
2. **Modify a byte inside the tarball** — simulates corruption or a man-in-the-middle attack
3. **Run installer** — expect immediate rejection before any staging occurs

Expected output: `REJECTED: manifest signature invalid` or `checksum mismatch`

### Downgrade rejection

**What you're testing:** Once on v1.1, the ECU must not accept a v1.0 package even if it is correctly signed.

1. **Ensure ECU is on v1.1** — run the full demo or install v1.1 manually
2. **Attempt to install v1.0** — the installer compares versions before staging

```bash
python3 Installer/installer.py packages/motorecu_v1.0.tar.gz
```

Expected: `REJECTED: downgrade not allowed (1.1 -> 1.0)`

---

## 7. Observability Checks

After any demo or manual test, inspect these files to confirm the OTA pipeline behaved correctly.

```bash
# Structured OTA log — installer, bootloader, and health monitor events
cat Virtual_ECU/MotorECU/logs/ota.log

# ECU version state — current version, active/pending slots
cat Virtual_ECU/MotorECU/config/version.json

# Live heartbeat (should update every ~1s while ECU is running)
watch -n1 cat Virtual_ECU/MotorECU/runtime/heartbeat.txt

# Running ECU PID — confirms ECU process is alive
cat Virtual_ECU/MotorECU/runtime/ecu.pid
```

| File | What it tells you |
|------|-------------------|
| `ota.log` | Chronological log of verify, stage, activate, health check, and rollback events |
| `version.json` | Authoritative state: `current_version`, `active_slot`, `pending_slot` |
| `heartbeat.txt` | Timestamp updated by the ECU process every ~1s; stale = unhealthy |
| `ecu.pid` | Process ID of the running virtual ECU firmware |

---

## 8. Docker-Specific Testing

All demo and test commands work identically inside the dev container.

```bash
# Build image and show status — compiles all components in the Docker image
docker compose up --build

# Interactive dev shell — enter container to run tests manually
docker compose run dev bash

# Run OTA server (exposed on host port 8080) — starts only the FastAPI service
docker compose up ota_server

# From host machine (with ota_server running):
curl http://localhost:8080/health
```

Inside the dev container, all demo and test commands work the same as native.

---

## 9. Demo Recording (Optional)

For a timed, presentation-ready run with consistent output:

```bash
FAST=1 ./Scripts/record_demo.sh
```

**What it does:** Wraps `run_demo.sh` with timing banners and formatted output suitable for live demos.

With asciinema recording:

```bash
RECORD=1 ./Scripts/record_demo.sh
# Output: demo.cast
```

**What it does:** Same demo, but records terminal session to `demo.cast` for playback or sharing.

---

## Test Matrix — Quick Reference

| Test | Command | What it does | Pass criteria |
|------|---------|--------------|---------------|
| Signing | `python3 Tests/test_signing.py` | Ed25519 sign/verify + tampered manifest detection | `All signing/verification tests passed.` |
| Tamper | `python3 Tests/test_tamper.py` | Corrupted firmware rejected by installer | `All tamper rejection tests passed.` |
| Downgrade | `python3 Tests/test_downgrade.py` | Version compare logic + installer blocks downgrade | `All downgrade protection tests passed.` |
| Full OTA | `FAST=1 ./Scripts/run_demo.sh` | v1.0 → v1.1 success → v1.2-broken auto-rollback | Final version 1.1, rollback logged |
| Cloud OTA | `./Scripts/run_cloud_demo.sh` | Same as full OTA via FastAPI server + OTA client | Same as full OTA |
| Fleet | `FAST=1 ./Scripts/run_fleet_demo.sh` | Updates MotorECU + BrakeECU + BatteryECU to v1.1 | All 3 ECUs at v1.1 |
| Server health | `curl localhost:8080/health` | Confirms OTA cloud server is running | `{"status":"ok",...}` |

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
