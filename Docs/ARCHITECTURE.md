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

> See [Cloud Integration](#cloud-integration) for the full connection model, API details, and trust boundaries.

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

> See [Cloud Integration](#cloud-integration) for the poll/download sequence and fleet orchestration over HTTP.

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

## Cloud Integration

This section explains how the OTA cloud server connects to the rest of the system, what communication actually happens over the network, and where the trust boundaries lie.

### What "Cloud" Means in This Project

The **OTA_Cloud** component is a **local simulated cloud backend** — not AWS, Azure, or a remote OEM server. It is a FastAPI application (`OTA_Cloud/server.py`) that runs on your machine (typically `localhost:8080`) and serves pre-built signed firmware packages from the `packages/` directory.

In a real vehicle OTA system, this role would be played by an OEM backend (e.g. Tesla, Rivian, or a tier-1 supplier cloud). This project models that pattern using plain HTTP on the same host, so the full pipeline can be demonstrated without external infrastructure.

**Important:** The cloud is only a **package delivery layer**. It does not install firmware, verify signatures, talk to the bootloader, or know what version is running on any ECU.

### Connection Model

There is exactly **one network connection** in this project: **OTA_Client → OTA_Cloud** over HTTP.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         "Vehicle" (local machine)                        │
│                                                                          │
│  ┌─────────────┐    HTTP REST     ┌─────────────┐                        │
│  │ OTA_Client  │ ◄──────────────► │ OTA_Cloud   │  (may be same host     │
│  │             │  poll + download │ (FastAPI)   │   or separate container)│
│  └──────┬──────┘                  └──────┬──────┘                        │
│         │                                │                               │
│         │ subprocess                     │ reads files                    │
│         ▼                                ▼                               │
│  ┌─────────────┐                  packages/*.tar.gz                       │
│  │ Installer   │                                                          │
│  └──────┬──────┘                                                          │
│         │ subprocess                                                      │
│         ▼                                                                 │
│  ┌─────────────┐    subprocess    ┌─────────────┐    heartbeat file       │
│  │ Bootloader  │ ───────────────► │ Virtual ECU │ ◄──────────────────┐   │
│  └─────────────┘                  └─────────────┘                     │   │
│         ▲                                                             │   │
│         │ rollback                                                    │   │
│  ┌──────┴──────┐                                                      │   │
│  │Health_Monitor│─────────────────────────────────────────────────────┘   │
│  └─────────────┘                                                          │
│                                                                          │
│  ◄── No network connection to cloud from here                           │
└──────────────────────────────────────────────────────────────────────────┘
```

Components below the client (Installer, Bootloader, Virtual ECU, Health Monitor) run **entirely on the vehicle side** with no cloud involvement. If the server goes down after a package is downloaded, the install pipeline still works.

### Trust Boundary

Security follows the **production OTA principle: trust is always verified on the vehicle, never on the cloud.**

| Responsibility | Cloud server | OTA client / installer (vehicle) |
|----------------|--------------|----------------------------------|
| Host signed packages | Yes | No |
| Know ECU current version | No | Yes (reads `version.json`) |
| Verify Ed25519 signature | No | Yes |
| Verify SHA-256 checksum | No | Yes |
| Block downgrades | No | Yes |
| Write to flash slots | No | No (bootloader only) |
| Health monitoring / rollback | No | Yes (health monitor) |

The cloud can serve any signed package that exists in `packages/`. The vehicle decides whether to accept, stage, and activate it. A malicious or compromised server cannot bypass signature verification — the vehicle holds the public key (`Tools/keys/ota_public_key.pem`).

### What the Cloud Server Does

**File:** `OTA_Cloud/server.py`  
**Runtime:** `uvicorn OTA_Cloud.server:app --host 0.0.0.0 --port 8080`

On startup and on every request, the server **scans** the `packages/` directory:

1. List all `*.tar.gz` files
2. Open each tarball and read `manifest.json` (without extracting to disk)
3. Build an in-memory catalog keyed by ECU name and version
4. Serve catalog metadata and file downloads via REST

The server is **stateless** — no database, no session store, no ECU registry. If you add a new `.tar.gz` to `packages/`, the next request picks it up automatically.

Logging uses the shared `ota_log` helper with the `[cloud]` component tag, e.g.:

```
[INFO] [cloud] Update check for MotorECU — latest v1.2
[INFO] [cloud] Serving motorecu_v1.1.tar.gz
```

### What the Cloud Server Does NOT Do

- **Push updates** — there is no WebSocket, MQTT, or server-initiated connection; the client must poll
- **Track vehicle state** — the server never reads `version.json` or knows what is installed
- **Authenticate vehicles** — no API keys, TLS client certs, or VIN validation (could be added in a production system)
- **Sign packages** — signing happens offline via `Scripts/package_generator.py` before upload to `packages/`
- **Install or activate firmware** — download only
- **Communicate with bootloader or ECU** — no direct connection exists

### REST API Reference

Base URL: `http://localhost:8080` (configurable via `SERVER_URL`)

#### `GET /health`

Health check for monitoring and demo script readiness probes.

**Response:**
```json
{
  "status": "ok",
  "packages_dir": "/app/packages"
}
```

#### `GET /updates/{ecu}`

Returns the latest package and full list of available versions for an ECU. Used by the client to discover updates.

**Example:** `GET /updates/MotorECU`

**Response:**
```json
{
  "ecu": "MotorECU",
  "latest": {
    "ecu": "MotorECU",
    "version": "1.2",
    "size": 12345,
    "checksum": "sha256:abc123...",
    "package": "motorecu_v1.2.tar.gz",
    "download_url": "/packages/MotorECU/1.2"
  },
  "available": [
    { "ecu": "MotorECU", "version": "1.0", "download_url": "/packages/MotorECU/1.0", ... },
    { "ecu": "MotorECU", "version": "1.1", "download_url": "/packages/MotorECU/1.1", ... },
    { "ecu": "MotorECU", "version": "1.2", "download_url": "/packages/MotorECU/1.2", ... }
  ]
}
```

Returns `404` if no packages exist for the requested ECU.

#### `GET /packages/{ecu}/{version}`

Downloads the signed `.tar.gz` package as a file attachment.

**Example:** `GET /packages/MotorECU/1.1`  
**Response:** Binary stream (`application/gzip`) of `motorecu_v1.1.tar.gz`

Returns `404` if the ECU/version combination is not in the catalog or the file is missing from disk.

#### `GET /catalog`

Returns the full package catalog for all ECUs (useful for debugging and demos).

**Example response:**
```json
{
  "MotorECU": {
    "1.0": { "ecu": "MotorECU", "version": "1.0", "download_url": "/packages/MotorECU/1.0", ... },
    "1.1": { ... },
    "1.2": { ... }
  },
  "BrakeECU": {
    "1.1": { ... }
  }
}
```

### OTA Client — Cloud Interaction Flow

**File:** `OTA_Client/client.py`  
**Transport:** Python `urllib` (standard library HTTP, no extra client SDK)

The client is the **only component** that talks to the cloud. Here is the full sequence:

```
┌──────────┐                    ┌──────────┐                    ┌──────────┐
│  Client  │                    │  Cloud   │                    │ Installer│
└────┬─────┘                    └────┬─────┘                    └────┬─────┘
     │                                 │                               │
     │ 1. Read local version.json      │                               │
     │    (current = 1.0)              │                               │
     │                                 │                               │
     │ 2. GET /updates/MotorECU        │                               │
     │────────────────────────────────►│                               │
     │◄────────────────────────────────│                               │
     │    { latest: 1.1, available }   │                               │
     │                                 │                               │
     │ 3. Compare: 1.1 > 1.0 → update  │                               │
     │    available                    │                               │
     │                                 │                               │
     │ 4. GET /packages/MotorECU/1.1   │                               │
     │────────────────────────────────►│                               │
     │◄────────────────────────────────│                               │
     │    motorecu_v1.1.tar.gz         │                               │
     │                                 │                               │
     │ 5. Save to packages/            │                               │
     │                                 │                               │
     │ 6. install_package(local_path)  │                               │
     │─────────────────────────────────────────────────────────────────►│
     │                                 │                               │
     │                                 │         7. verify + stage +   │
     │                                 │            activate + grace   │
     │◄─────────────────────────────────────────────────────────────────│
     │    done                         │                               │
```

#### Step-by-step (mapped to code)

| Step | Action | Code location |
|------|--------|---------------|
| 1 | Read current ECU version from `Virtual_ECU/{ECU}/config/version.json` | `poll_for_update()` → `read_current_version()` |
| 2 | HTTP GET `{server}/updates/{ecu}` | `poll_for_update()` → `_get_json(updates_url)` |
| 3 | Pick target version (`--version` flag or `latest`); skip if not newer | `poll_for_update()` → `compare_versions()` |
| 4 | HTTP GET `{server}{download_url}` | `download_and_install()` → `_download()` |
| 5 | Save tarball to `packages/{name}.tar.gz` | `download_and_install()` |
| 6 | Hand off to installer (cloud no longer involved) | `download_and_install()` → `install_package()` |

Key client functions:

```python
# Poll server for available updates
updates_url = f"{server_url}/updates/{ecu}"
data = _get_json(updates_url)

# Download package
download_url = f"{server_url}{update_info['download_url']}"
_download(download_url, tmp_path)

# Install locally — same path as non-cloud demo
install_package(local_path, activate=..., grace_duration=..., ecu=...)
```

If the server is unreachable, the client raises:

```
Cannot reach OTA server at http://localhost:8080: <reason>
```

The bootloader and ECU are unaffected — they were never part of the HTTP conversation.

### Local Path vs Cloud Path

Both paths produce **identical results** after the package is available on disk. The only difference is how the `.tar.gz` gets to the vehicle.

| Aspect | Local path | Cloud path |
|--------|------------|------------|
| Entry point | `Installer/installer.py` directly | `OTA_Client/client.py` |
| Package source | Already in `packages/` (built by demo script) | Downloaded via HTTP from OTA_Cloud |
| Server required | No | Yes (`uvicorn` on port 8080) |
| Network traffic | None | 2 HTTP requests per update (poll + download) |
| Verify / stage / activate | Installer | Installer (after download) |
| Demo script | `run_demo.sh` (default) | `run_cloud_demo.sh` or `CLOUD=1 run_demo.sh` |

In `Scripts/run_demo.sh`, the switch is a single environment variable:

```bash
# Local path (default)
python3 Installer/installer.py packages/motorecu_v1.1.tar.gz --activate --grace-duration 32

# Cloud path (CLOUD=1)
python3 OTA_Client/client.py \
    --server http://localhost:8080 --ecu MotorECU --version 1.1 \
    --activate --grace-duration 32
```

### How Demo Scripts Wire Up the Cloud

#### `run_cloud_demo.sh`

Sets `CLOUD=1` and delegates to `run_demo.sh`:

```bash
CLOUD=1 FAST=1 bash Scripts/run_demo.sh
```

When `CLOUD=1`, `run_demo.sh` additionally:

1. Builds packages locally (the server does not create them — they must exist in `packages/` before the client polls)
2. Starts the server in the background:
   ```bash
   uvicorn OTA_Cloud.server:app --host 127.0.0.1 --port 8080 &
   ```
3. Waits for `GET /health` to succeed (up to 10 retries)
4. Runs installs via `OTA_Client/client.py` instead of `Installer/installer.py` directly
5. Stops the server on exit via `trap stop_ota_server EXIT`

#### `run_fleet_demo.sh`

Always uses the cloud path:

1. `init_ecu.sh all` — reset all ECUs to v1.0
2. Package v1.1 firmware for MotorECU, BrakeECU, BatteryECU into `packages/`
3. Start OTA cloud server on port 8080
4. Run `OTA_Client/fleet.py` to update each ECU sequentially

### Fleet Orchestration Over the Cloud

**File:** `OTA_Client/fleet.py`

The fleet orchestrator calls `run_client()` once per ECU, reusing the same cloud connection pattern. Each ECU update is an independent poll + download + install cycle.

```
fleet.py
  │
  ├─ For vehicle VIN001:
  │     ├─ run_client(server, MotorECU)   → GET /updates/MotorECU → GET /packages/... → install
  │     ├─ run_client(server, BrakeECU)   → same pattern
  │     └─ run_client(server, BatteryECU) → same pattern
  │
  └─ For vehicle VIN002:
        └─ (same ECUs — simulated multi-vehicle config)
```

Fleet configuration (`Scripts/fleet_config.json`):

```json
{
  "vehicles": [
    { "id": "VIN001", "ecus": ["MotorECU", "BrakeECU", "BatteryECU"] },
    { "id": "VIN002", "ecus": ["MotorECU", "BrakeECU", "BatteryECU"] }
  ]
}
```

In this simulation, all vehicles share the same local `Virtual_ECU/` directories — the VIN is used for logging and orchestration structure, not physical isolation.

### Docker Deployment

`docker-compose.yml` defines three services that share the same repo mount:

| Service | Container | Role |
|---------|-----------|------|
| `ota_server` | `sdv_ota_server` | Runs uvicorn, exposes **port 8080** to host |
| `dev` | `sdv_dev` | Interactive shell for running demos and client |
| `sdv_ota` | `sdv_ota` | Build image, show status on start |

Because both `ota_server` and `dev` mount `.` → `/app`, they see the **same `packages/` directory**. In a real deployment:

- **Cloud container** would only have access to `packages/` (or S3-backed storage)
- **Vehicle container** would only have the client, installer, bootloader, and ECU — no private signing key

Example: run server in one terminal, client in another:

```bash
# Terminal 1
docker compose up ota_server

# Terminal 2
docker compose run dev bash
python3 OTA_Client/client.py --server http://host.docker.internal:8080 --ecu MotorECU --version 1.1 --activate
```

When both run inside the same `dev` container, `http://localhost:8080` works because the demo scripts start uvicorn locally.

### Package Lifecycle (Cloud Perspective)

Understanding where packages come from clarifies the cloud's role:

```
Firmware binary (C)
        │
        ▼
Scripts/package_generator.py
  ├─ Compute SHA-256 checksum
  ├─ Sign manifest with Ed25519 private key
  └─ Create packages/motorecu_v1.1.tar.gz
        │
        ▼
packages/ directory on disk
        │
        ▼
OTA_Cloud scans directory → builds catalog → serves via HTTP
        │
        ▼
OTA_Client downloads → saves to packages/ (same or vehicle-side copy)
        │
        ▼
Installer verifies signature + checksum → stages → activates
```

The cloud never participates in signing or verification — it only distributes already-signed artifacts.

### Environment Variables

| Variable | Default | Used by | Effect |
|----------|---------|---------|--------|
| `CLOUD` | `0` | `run_demo.sh` | `1` = use OTA client + start server |
| `SERVER_URL` | `http://localhost:8080` | Client, demo scripts | Cloud server base URL |
| `FAST` | `0` | Demo scripts | Skip C rebuilds |
| `GRACE_V11` | `32` | Demo scripts | Grace period for v1.1 (seconds) |
| `GRACE_V12` | `12` | Demo scripts | Grace period for v1.2 (seconds) |

Client CLI flags:

```bash
python3 OTA_Client/client.py \
  --server http://localhost:8080 \   # cloud URL
  --ecu MotorECU \                   # target ECU
  --version 1.1 \                    # specific version (optional)
  --activate \                       # activate after stage
  --grace-duration 32                # health monitor window
```

### Failure Modes

| Scenario | What happens | Cloud involved? |
|----------|--------------|-----------------|
| Server not running | Client fails: `Cannot reach OTA server` | Yes — connection failed |
| Package not in `packages/` | Server returns 404 on `/updates/{ecu}` | Yes |
| Tampered download | Installer rejects: invalid signature or checksum | No — verified locally |
| Downgrade attempt | Installer rejects before staging | No |
| Broken firmware (v1.2) | Health monitor rolls back after activation | No |
| Server stops mid-download | Client HTTP error; install does not proceed | Yes |
| Server stops after download | Install continues normally | No — already local |

### Production Analogy

| This project | Real automotive OTA |
|--------------|----------------------|
| FastAPI on `localhost:8080` | OEM cloud backend (REST/gRPC API) |
| `packages/` folder on disk | S3, Azure Blob, or CDN |
| `OTA_Client` polling HTTP | In-vehicle OTA agent / telematics module |
| Ed25519 verify on vehicle | Same — always on-device before flash |
| `version.json` on filesystem | ECU NVM / secure storage |
| A/B slots + health monitor | Same pattern on real ECU hardware |
| No TLS / auth | Production would use HTTPS, mutual TLS, VIN auth |

The architecture intentionally mirrors production: **the cloud delivers packages; the vehicle verifies and installs locally.** The cloud never has direct access to flash slots or ECU runtime state.

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
