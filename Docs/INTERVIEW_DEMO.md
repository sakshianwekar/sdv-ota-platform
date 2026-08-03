# SDV OTA Platform — Interview Demo Guide

Use this document as your **copy-paste script** for live demos and technical interviews. Every command is listed in the order you should run it, with a short explanation of what it does and what to say while it runs.

**Verified end-to-end:** security tests, full OTA demo, cloud demo, and fleet demo all pass on macOS (native) and Linux (Docker).

---

## What to Say in 30 Seconds (Opening)

> "This is a simulated automotive OTA platform. A vehicle ECU polls a cloud server for signed firmware, verifies Ed25519 signatures and SHA-256 checksums locally, stages the update into an inactive A/B flash slot, activates it, and watches a health monitor. If the new firmware fails, it rolls back automatically — no human intervention."

---

## Recommended Demo Flow (~8 minutes)

| # | What you show | Time |
|---|---------------|------|
| 1 | One-time setup (Docker) | 2–3 min (first time only) |
| 2 | Security tests | ~10 s |
| 3 | Full OTA demo (happy path + rollback) | ~60 s |
| 4 | Cloud path demo | ~60 s |
| 5 | Fleet demo (3 ECUs) | ~60 s |
| 6 | Show logs / final state | ~30 s |

Run demos **one at a time**. If port 8080 is busy: `pkill -f "uvicorn OTA_Cloud"` before cloud or fleet demos.

---

## Part 1 — One-Time Setup (Docker, Recommended)

Run these once before the interview. They build the environment where all demos work.

### 1. Go to the project

```bash
cd sdv-ota-platform
```

**What it does:** Changes into the repo root. All scripts assume you are here (or inside the Docker container at `/app`).

---

### 2. Build Docker images and start services

```bash
docker compose up --build
```

**What it does:**
- Builds an Ubuntu 24.04 image with `gcc`, `python3`, and Python deps (`fastapi`, `uvicorn`, `cryptography`)
- Compiles all firmware (motor v1.0, v1.1, v1.2-broken, brake, battery), bootloader, and health monitor
- Generates OTA signing keys if missing (or if private/public keys are mismatched)
- Starts three services: `sdv_ota` (status), `ota_server` (port 8080), `dev` (interactive shell)

**What to say:** "We containerize the whole toolchain so the demo runs the same on any machine."

**Pass criteria:** Build finishes without errors. Optional check from another terminal:

```bash
curl http://localhost:8080/health
```

Expected: `{"status":"ok","packages_dir":"/app/packages"}`

---

### 3. Enter the dev container

```bash
docker compose run --rm dev bash
```

**What it does:** Starts an interactive bash shell inside the container with the repo mounted at `/app`. All demo commands run from here.

**What to say:** "This is our dev environment — same tools as on a build server, isolated from the host."

Your prompt will show `root@<container-id>:/app#`. That is normal.

---

### Alternative — Native Setup (no Docker)

Only if you cannot use Docker. On Apple Silicon / macOS you must build natively (Linux binaries from Docker will not run on the host).

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
pip3 install cryptography fastapi "uvicorn[standard]"
```

| Command | What it does |
|---------|--------------|
| `make -C Firmware/motor_ecu rebuild` | Compiles v1.0 MotorECU firmware binary |
| `make -C Firmware/motor_ecu_v1.1 rebuild` | Compiles v1.1 (healthy "eco mode") firmware |
| `make -C Firmware/motor_ecu_v1.2_broken rebuild` | Compiles v1.2 (signed but stops heartbeat → triggers rollback) |
| `make -C Firmware/brake_ecu rebuild` | Compiles BrakeECU firmware |
| `make -C Firmware/battery_ecu rebuild` | Compiles BatteryECU firmware |
| `make -C Bootloader rebuild` | Compiles the A/B slot bootloader |
| `make -C Health_Monitor rebuild` | Compiles the grace-period health watcher |
| `python3 Tools/gen_keys.py` | Creates Ed25519 signing key pair in `Tools/keys/` |
| `pip3 install ...` | Installs Python deps for installer, OTA client, and cloud server |

---

## Part 2 — Security Tests (~10 seconds)

**What to say:** "Before any firmware touches flash, we prove the security layer works in isolation."

```bash
python3 Tests/test_signing.py && \
python3 Tests/test_tamper.py && \
python3 Tests/test_downgrade.py
```

| Command | What it does | Expected output |
|---------|--------------|-----------------|
| `test_signing.py` | Signs a manifest with Ed25519, verifies it passes; tampered manifest fails | `All signing/verification tests passed.` |
| `test_tamper.py` | Flips a byte in firmware, confirms installer rejects the package | `All tamper rejection tests passed.` |
| `test_downgrade.py` | Tries to install v1.0 over v1.1, confirms downgrade is blocked | `All downgrade protection tests passed.` |

---

## Part 3 — Full OTA Demo (~60 seconds) ⭐ Main Demo

**What to say:** "This is the full story: successful update, then a broken update that rolls back automatically."

```bash
FAST=1 ./Scripts/run_demo.sh
```

**What it does (step by step inside the script):**

| Step | What happens |
|------|--------------|
| Reset | Stops ECU, copies v1.0 to both flash slots, sets `version.json` to 1.0 on slot A |
| Package | Creates signed `.tar.gz` for v1.0, v1.1, and v1.2-broken |
| Install v1.1 | Verifies signature → stages to slot B → activates → 32s health grace period |
| Confirm v1.1 | Prints bootloader status — should show version 1.1, slot B |
| Install v1.2-broken | Same flow; v1.2 stops sending heartbeats after ~6s |
| Rollback | Health monitor hits 3 failures → calls `bootloader rollback` → back to v1.1 |
| Assert | Checks final version is still **1.1** |

**Pass criteria:**

```
ASSERT PASSED: final version is 1.1
Demo complete (XXs)
```

**Talk track while waiting on grace periods:**
1. "We start on v1.0, slot A."
2. "v1.1 is signed, staged to slot B, activated."
3. "Health monitor watches for 32 seconds — heartbeat every second."
4. "v1.1 passes. Now v1.2 — legitimately signed, but behaviorally broken."
5. "Three missed heartbeats → automatic rollback. Still on v1.1."

---

## Part 4 — Cloud Path Demo (~60 seconds)

**What to say:** "Same story, but the update comes over HTTP — closer to a real vehicle architecture."

```bash
./Scripts/run_cloud_demo.sh
```

**What it does:**
- Sets `CLOUD=1` and runs the same demo as Part 3
- Starts a FastAPI server on port 8080
- OTA client polls `GET /updates/MotorECU`, downloads `GET /packages/MotorECU/{version}`
- Installer still verifies and installs locally after download

**Pass criteria:** Same as Part 3 — `ASSERT PASSED: final version is 1.1`

**Optional — show the server API:**

```bash
curl http://localhost:8080/health
curl http://localhost:8080/updates/MotorECU
curl http://localhost:8080/catalog
```

| Endpoint | What it does |
|----------|--------------|
| `/health` | Confirms server is running |
| `/updates/MotorECU` | Lists available firmware versions for MotorECU |
| `/catalog` | Full package catalog across all ECUs |

---

## Part 5 — Fleet Demo (~60 seconds)

**What to say:** "One orchestrator updates motor, brake, and battery ECUs in a single campaign."

```bash
FAST=1 ./Scripts/run_fleet_demo.sh
```

**What it does:**

| Step | What happens |
|------|--------------|
| Initialize | Resets MotorECU, BrakeECU, BatteryECU to v1.0 |
| Package | Creates signed v1.1 packages for all three ECUs |
| Start server | Launches OTA cloud on port 8080 |
| Fleet update | `OTA_Client/fleet.py` updates each ECU via the cloud |
| Status | Prints version for all three ECUs |

**Verify all ECUs reached v1.1:**

```bash
./Bootloader/build/bootloader --ecu MotorECU status
./Bootloader/build/bootloader --ecu BrakeECU status
./Bootloader/build/bootloader --ecu BatteryECU status
```

**Pass criteria:** All three show `version: 1.1` and fleet summary shows `Updated: 3  Failed: 0`.

---

## Part 6 — Show Observability (Optional, ~30 seconds)

**What to say:** "Every step is logged — installer, bootloader, health monitor."

```bash
cat Virtual_ECU/MotorECU/logs/ota.log
cat Virtual_ECU/MotorECU/config/version.json
cat Virtual_ECU/MotorECU/runtime/heartbeat.txt
```

| File | What it shows |
|------|---------------|
| `ota.log` | Chronological OTA events (verify, stage, activate, rollback) |
| `version.json` | Current version, active slot, pending slot |
| `heartbeat.txt` | Unix timestamp updated every ~1s while ECU is healthy |

---

## Quick Reference — All Commands in Order

Copy this block for a full interview run (inside Docker dev shell or native after setup):

```bash
# 1. Security
python3 Tests/test_signing.py && python3 Tests/test_tamper.py && python3 Tests/test_downgrade.py

# 2. Full OTA (local installer path)
FAST=1 ./Scripts/run_demo.sh

# 3. Cloud path (FastAPI + OTA client)
./Scripts/run_cloud_demo.sh

# 4. Fleet (3 ECUs)
FAST=1 ./Scripts/run_fleet_demo.sh

# 5. Verify fleet state
./Bootloader/build/bootloader --ecu MotorECU status
./Bootloader/build/bootloader --ecu BrakeECU status
./Bootloader/build/bootloader --ecu BatteryECU status

# 6. Show logs
cat Virtual_ECU/MotorECU/logs/ota.log
```

---

## Architecture (If They Ask "How Does It Work?")

```
OTA_Cloud (FastAPI)     → serves signed packages
    ↓ HTTP
OTA_Client (Python)     → poll, download, verify
    ↓
Installer (Python)      → extract, verify signature + checksum
    ↓
Bootloader (C)          → stage to inactive slot, activate, rollback
    ↓
Virtual ECU (C)         → runs firmware, writes heartbeat every 1s
    ↓
Health Monitor (C)      → grace period → 3 failures → auto rollback
```

**Key design points to mention:**
- **A/B slots** — never overwrite the running firmware
- **Ed25519 + SHA-256** — authenticity and integrity, both required
- **Grace-period rollback** — 3 consecutive heartbeat failures trigger rollback with no human input
- **Downgrade protection** — installer refuses older versions

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `manifest signature invalid` | Signing keys out of sync with packages | `python3 Tools/gen_keys.py` then re-run demo (re-packages automatically) |
| `cannot execute binary file` | Linux binaries on macOS host | Use Docker, or `make -C ... rebuild` natively on host |
| `permission denied: ./Scripts/run_demo.sh` | Scripts not executable | `chmod +x Scripts/*.sh` |
| Port 8080 in use | Previous OTA server still running | `pkill -f "uvicorn OTA_Cloud"` |
| Fleet demo skips MotorECU | MotorECU already on v1.1 from prior demo | Run fleet demo on a fresh state, or run it before other demos |
| Demo fails with stale heartbeat | ECU binary not executable in flash slot | Fixed in bootloader (chmod after copy); rebuild bootloader: `make -C Bootloader rebuild` |
| `root@...` in Docker prompt | Normal — container runs as root | Type `exit` to leave container |

---

## Exit Docker

```bash
exit
```

**What it does:** Leaves the dev container and returns to your Mac terminal.

---

## Related Docs

- [TESTING.md](./TESTING.md) — detailed test guide with step-by-step flows
- [DEMO_COMMANDS.md](./DEMO_COMMANDS.md) — granular command cheat sheet
- [ARCHITECTURE.md](./ARCHITECTURE.md) — full system design
