# SDV OTA Platform — LinkedIn Launch Kit

Ready-to-use content for **Sakshi** + **Tejas**.  
Repo: https://github.com/sakshianwekar/sdv-ota-platform

**Same-day posts:**
1. Sakshi → PDF carousel (case study)
2. Tejas → short animated video (how it works)
3. Both → GitHub link in first comment + cross-comment + repost

---

## A. Ready-made assets (already generated)

| Asset | Path | Use on LinkedIn |
|-------|------|-----------------|
| **PDF carousel (9 slides)** | [`Docs/linkedin-assets/sdv-ota-linkedin-carousel.pdf`](linkedin-assets/sdv-ota-linkedin-carousel.pdf) | Sakshi posts as **Document** |
| **Architecture diagram** | [`Docs/linkedin-assets/ota-architecture-diagram.png`](linkedin-assets/ota-architecture-diagram.png) | Tejas video / image posts; also embedded in PDF slide 4 |
| Slide previews | `Docs/linkedin-assets/preview/slide-01.png` … `slide-09.png` | Quick visual check before posting |

Regenerate anytime:

```bash
pip install reportlab pillow
python3 Scripts/generate_linkedin_assets.py
```

## A2. What else to prepare

| Asset | Format | Tool | Owner |
|-------|--------|------|-------|
| Animated explainer | MP4 (45–75 sec) | CapCut or Canva Video | Tejas |
| Demo proof screenshot | PNG (optional) | Terminal screenshot | Either |
| Captions + comments | Text | This file | Both |

---

## B. How to prepare with tools

### 1) PDF carousel

**Ready file:** `Docs/linkedin-assets/sdv-ota-linkedin-carousel.pdf`

On LinkedIn: **Start a post → Document → upload this PDF**.

To redesign later in Canva: Custom size `1080 x 1350`, copy Section C text, or start from the generated PDF slides.

### 2) Architecture diagram

**Ready file:** `Docs/linkedin-assets/ota-architecture-diagram.png`

Use in Tejas’s video, as a standalone image post, or when redesigning slides.

### 3) Animated video (CapCut — recommended)

1. Install / open [CapCut](https://www.capcut.com) (desktop or phone).
2. New project → ratio **9:16** (mobile) or **1:1**.
3. Add text scenes using **Section D** script (one scene per beat).
4. Add simple motion: fade / slide in arrows between components.
5. Optional: import architecture PNG + 1 terminal screenshot.
6. Add **on-screen captions** (many people watch muted).
7. Export **MP4**, 720p or 1080p, **45–75 seconds**.
8. LinkedIn: **Start a post → Video → upload MP4**.

**Canva Video alternative**
1. Canva → **Video** → 1080×1920 or 1080×1080.
2. Use “animated text” / “process flowchart” elements.
3. Paste Section D lines on each scene.
4. Download **MP4**.

**No-animation fallback (still professional)**
- Screen-record Docker/demo for ~60s (`run_demo` happy path + rollback).
- Overlay titles in CapCut (“Signed update”, “Health fail”, “Auto-rollback”).

### 4) Demo screenshot (optional but strong)

After a successful demo, capture:
- `version: 1.1`
- log line about automatic rollback

Put on carousel slide 6 or last 2 seconds of video.

---

## C. Carousel slide text (copy into Canva/PPT)

**Slide 1 — Hook**  
Title: How do cars update firmware without bricking an ECU?  
Subtitle: A software simulation of real automotive OTA safety  
Footer: Sakshi Anwekar × Tejas

**Slide 2 — Problem**  
Title: The real risk  
Bullets:
- Unsigned or tampered firmware
- Overwriting the running image
- No automatic recovery when update fails

**Slide 3 — Application**  
Title: Where this matters  
Bullets:
- Software-Defined Vehicles (SDV)
- Remote ECU firmware updates
- Fleet software delivery

**Slide 4 — Solution pipeline**  
Title: Our OTA pipeline  
Line:
OTA Cloud (FastAPI) → Client → Installer → Bootloader (C) → Virtual ECUs → Health Monitor  
(Paste architecture image here)

**Slide 5 — Safety: A/B slots**  
Title: Never overwrite running firmware  
Body: New update is staged into the inactive A/B flash slot, then activated only after verification.

**Slide 6 — Safety: trust**  
Title: Cryptographic verification  
Bullets:
- Ed25519 signature = authenticity
- SHA-256 checksum = integrity
- Tamper + downgrade rejected before flash

**Slide 7 — Proof**  
Title: What we demonstrated  
Bullets:
- v1.0 → v1.1 healthy update stays active
- Signed-but-broken v1.2 fails health checks → auto-rollback
- Fleet update: Motor + Brake + Battery ECUs

**Slide 8 — Team**  
Title: Built by two engineers  
Sakshi: [e.g. OTA Cloud, Client, Installer, packaging, tests]  
Tejas: [e.g. Bootloader, Health Monitor, Virtual ECUs, fleet path]

**Slide 9 — CTA**  
Title: Want the repo + demo?  
Body: Links in the first comment  
Question: Signing or health-based rollback — which matters more? (We built both.)  
Roles: Open to Embedded / Backend / Automotive software conversations

---

## D. 60-second video script (Tejas)

Use as **voiceover and/or on-screen text**.

| Time | On-screen text | Speak (optional) |
|------|----------------|------------------|
| 0–8s | Remote firmware updates can brick an ECU | How do you update vehicle firmware without risking a brick? |
| 8–20s | Cloud → Client → Installer → Bootloader → ECU | We built a full SDV OTA simulation: cloud serves signed packages, client verifies, bootloader installs. |
| 20–35s | Signed packages + A/B flash slots | Ed25519 signing proves authenticity. A/B slots mean we never overwrite the running image. |
| 35–55s | Broken update → health fail → AUTO-ROLLBACK | Even a signed bad update can fail at runtime. Our health monitor detects that and rolls back automatically. |
| 55–70s | Motor · Brake · Battery \| Built by Sakshi & Tejas \| GitHub in comments | Works for a multi-ECU fleet too. Built with Sakshi. Repo in the comments. |

End card text:
`SDV OTA Platform`  
`Sakshi Anwekar × Tejas`  
`github.com/sakshianwekar/sdv-ota-platform`

---

## E. Captions (paste-ready)

### Sakshi — carousel post

```text
How do cars get software updates without bricking an ECU?

Tejas and I built a full Software-Defined Vehicle OTA simulation that mirrors real update safety:

→ Signed firmware (Ed25519 + checksum)
→ A/B flash slots (never overwrite running firmware)
→ Health monitoring with automatic rollback

Flow:
OTA Cloud (FastAPI) → Client → Installer → Bootloader (C) → Virtual ECUs → Health Monitor

What we proved end-to-end:
• Healthy update: v1.0 → v1.1 stays active
• Broken update: signed v1.2 fails health checks → auto-rollback
• Tamper / downgrade attempts rejected before flash
• Fleet path: Motor + Brake + Battery ECUs

Built with @Tejas
I focused on: [Sakshi ownership]
Tejas focused on: [Tejas ownership]

Swipe for architecture + safety design.

Question for engineers & recruiters:
In OTA systems, what matters more — cryptographic verification or runtime health checks?
(We implemented both as separate layers.)

Links + demo in the first comment.

#SoftwareDefinedVehicle #OTA #EmbeddedSystems #AutomotiveSoftware #Python
```

**Sakshi first comment:**

```text
🔗 GitHub: https://github.com/sakshianwekar/sdv-ota-platform
▶️ Demo: docker compose up --build → run happy-path + rollback + fleet demos
Happy to walk hiring managers / embedded & backend teams through the architecture.
```

### Tejas — video post

```text
Cryptographic signature ≠ safe firmware.

While building our SDV OTA platform with @Sakshi Anwekar, that became the key lesson.

A package can be:
✅ correctly signed
✅ checksum-valid
❌ still dangerous at runtime

So we separated safety into two layers:
1) Verify authenticity before install (Ed25519 + SHA-256)
2) Watch health after activate — if heartbeats fail, bootloader auto-rollbacks

I focused on: [Tejas ownership]
Sakshi focused on: [Sakshi ownership]

This short animation shows the flow:
remote update → secure verify → A/B stage → activate → health watch → rollback if needed.

If you work in automotive / embedded / backend:
Would you ship OTA with only signing, or require health-based rollback too?

Repo + demo in comments.

#SoftwareDefinedVehicle #OTA #EmbeddedSystems #AutomotiveSoftware #Python
```

**Tejas first comment:**

```text
🔗 Project repo: https://github.com/sakshianwekar/sdv-ota-platform
Full architecture carousel from Sakshi today: [paste Sakshi post link]
Happy to explain the stage → activate → rollback control flow.
```

---

## F. Same-day posting order

| Time | Action |
|------|--------|
| 9:00 | Sakshi posts PDF carousel |
| 9:02 | Sakshi adds GitHub first comment; Tejas likes + writes strong comment |
| 9:20 | Tejas posts animated video |
| 9:22 | Tejas adds GitHub first comment; Sakshi likes + comments |
| 9:30–10:30 | Both reply to every comment |
| 10:30 | Both repost each other’s post with a 2-line intro |

**Tejas comment on Sakshi’s post:**
```text
Proud to co-build this with you, Sakshi.
My side was [bootloader / health monitor / ECU runtime].
Signing proves authenticity — health-based rollback protects the vehicle after activation.
Happy to walk through the C-side flow if useful.
```

**Sakshi comment on Tejas’s post:**
```text
Exactly — signature ≠ runtime safety.
Full end-to-end case study in my carousel today: [link]
Repo: https://github.com/sakshianwekar/sdv-ota-platform
```

---

## G. Ownership lines (fill once, reuse everywhere)

Suggested (edit if needed):

- **Sakshi:** OTA Cloud (FastAPI), OTA Client, Installer, packaging, security tests  
- **Tejas:** Bootloader (C), Health Monitor, Virtual ECUs, firmware / fleet path  

---

## H. Optional evening poll (one person only)

Question: For vehicle OTA safety, what’s the #1 must-have?  
Options:
1. Signed packages only  
2. A/B slots  
3. Auto-rollback on health fail  
4. All three together  

Caption tip: mention you implemented all three; put GitHub in comments.
