# Siphon v2.0

**Siphon** is a private, unindexed, PWA-enabled video extraction and download platform. Install it on Android, iOS, Windows, and macOS. Built for stealth, speed, and mobile-first UX.

---

## What It Does

Paste any video URL → Siphon scans it with a stealth browser → selects resolution → downloads via background queue → delivers to your device. Everything is ephemeral. Files auto-delete after transfer and orphaned files get wiped every 30 minutes.

---

## Feature Overview

### Core Engine
| Feature | Description |
|---------|-------------|
| **Stealth Browser** | Playwright with anti-detection patches (navigator.webdriver removal, fake plugins, permission spoofing) |
| **Network Interception** | Captures hidden `.m3u8`, `.mpd`, `.mp4` manifests before yt-dlp even runs |
| **yt-dlp Integration** | Format extraction, chunk downloading, metadata retrieval |
| **FFmpeg Pipeline** | Automatic muxing/conversion to MP4 (H.264 + AAC) or MP3 |
| **Proxy Support** | Single proxy or rotating pool (round-robin / random) |
| **User-Agent Rotation** | Configurable list of UAs to evade fingerprinting |

### Download Modes
| Mode | Endpoint | Description |
|------|----------|-------------|
| **Video** | `POST /api/download` | Select exact resolution (360p–4K) |
| **Audio Only** | `POST /api/download/audio` | Extract just audio (MP3, AAC, M4A) |
| **Batch** | `POST /api/download/batch` | Queue up to 10 URLs at once |

### Real-Time Progress
- **WebSocket** (`/api/ws/job/{id}`): Live status updates with 1.5s heartbeat
- **HTTP Polling Fallback**: `GET /api/download/{id}/status` every 2s
- Auto-fallback if WebSocket unavailable

### Persistence & Analytics
- **SQLite Database**: Job history, download stats, metadata
- **Download History**: `/api/history` — browse past downloads with thumbnails
- **Admin Dashboard**: `/api/admin/health` — Redis, Celery, FFmpeg, Playwright status
- **Admin Stats**: `/api/admin/stats` — completed/failed/queued counts, total bytes
- **Structured Logging**: JSON format with request timing, IP, user-agent

### Security & Cleanup
- **Security Headers**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, CSP
- **Gzip Compression**: All responses above 1KB
- **Rate Limiting**: Configurable per-endpoint (`slowapi`)
- **Instant File Delete**: `finally` block on StreamingResponse unlinks file immediately after transfer
- **Orphan Cleanup**: Celery Beat deletes files older than 30 minutes every 10 minutes
- **Optional API Key**: Gate access with `API_KEY` env var
- **Optional Admin Token**: Protect admin endpoints

### PWA — Installable Everywhere
| Platform | Install Method |
|----------|---------------|
| **Android** | Chrome banner → one tap install |
| **iOS** | Safari Share → Add to Home Screen |
| **Windows** | Chrome/Edge address bar → Install icon |
| **macOS** | Chrome menu → Install Siphon |

- **Web App Manifest**: `display: standalone`, `orientation: portrait`, maskable icons
- **Service Worker**: Offline shell caching, push notification ready
- **Your Logo**: Custom 500×500 icon on every screen, home screen, and splash

### Frontend UX
| Feature | Description |
|---------|-------------|
| **Toast Notifications** | Success/error/info banners with auto-dismiss |
| **Offline Banner** | Detects network loss, shows warning |
| **Settings Panel** | WebSocket toggle, haptic toggle, auto-download, default resolution, custom server URL |
| **Download History** | Browse past downloads with thumbnails, file sizes, dates |
| **Batch Input** | Paste up to 10 URLs, one per line |
| **Audio Toggle** | Switch between video + audio and audio-only modes |
| **Keyboard Shortcuts** | `Ctrl+Enter` = scan, `Esc` = reset/close, `B` = batch, `S` = settings |
| **Haptic Feedback** | Vibration patterns on mobile (light/medium/heavy/success/warning/error) |
| **Web Share API** | Native share sheet on Android/iOS |
| **QR Code** | Generate QR for any completed download to share |
| **Error Boundary** | Graceful crash recovery with reload button |
| **Deep Linking** | `?url=https://...` auto-loads the URL on open |
| **Dark Mode** | Permanent dark theme optimized for OLED |

---

## Architecture

```
siphon/
├── backend/                 # FastAPI + Celery + Redis + SQLite
│   ├── app/
│   │   ├── main.py          # Entry point, all routers & middleware
│   │   ├── config.py        # Pydantic Settings (env vars)
│   │   ├── celery_app.py    # Celery config (concurrency=2, beat schedule)
│   │   ├── database.py      # SQLAlchemy models + repositories
│   │   ├── middleware.py    # Structured logging, security headers, Gzip
│   │   ├── routers/
│   │   │   ├── probe.py     # Video & audio probe endpoints
│   │   │   ├── download.py  # Video/audio/batch download + stream + status
│   │   │   ├── websocket.py # Real-time WebSocket progress
│   │   │   ├── admin.py     # Health, stats, jobs, cleanup
│   │   │   └── history.py   # Download history list
│   │   ├── services/
│   │   │   ├── extractor.py # Playwright stealth + yt-dlp engine
│   │   │   ├── proxy.py     # Single proxy wrapper
│   │   │   ├── proxy_pool.py # Rotating proxy pool
│   │   │   └── cleanup.py   # File lifecycle utilities
│   │   └── tasks/
│   │       └── download.py  # Celery tasks (video + audio + cleanup)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vite + React + TypeScript + Tailwind
│   ├── public/              # PWA icons, manifest, service worker
│   ├── src/
│   │   ├── App.tsx          # Main app with all features wired
│   │   ├── components/        # 13 UI components
│   │   └── hooks/             # 6 custom hooks
│   ├── Dockerfile
│   └── package.json
├── temp/downloads/          # Ephemeral storage (auto-cleaned)
├── docker-compose.yml
├── DEPLOY.md
└── README.md
```

---

## API Reference

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/probe` | POST | `{ url }` | Extract video formats & resolutions |
| `/api/probe/audio` | POST | `{ url }` | Extract audio formats & bitrates |
| `/api/download` | POST | `{ url, height }` | Queue video download |
| `/api/download/audio` | POST | `{ url, format, quality }` | Queue audio-only download |
| `/api/download/batch` | POST | `{ urls[], height }` | Queue up to 10 downloads |
| `/api/download/{id}/status` | GET | — | Poll job status |
| `/api/download/{id}/file` | GET | — | Stream MP4/MP3 with `Content-Disposition: attachment` |
| `/api/ws/job/{id}` | WS | — | Real-time WebSocket progress |
| `/api/history` | GET | — | Recent download history |
| `/api/admin/health` | GET | — | Service health dashboard |
| `/api/admin/stats` | GET | `?token=` | Download stats |
| `/api/admin/jobs` | GET | `?token=` | Recent job list |
| `/api/admin/cleanup` | POST | `?token=` | Force orphan cleanup |

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+, Node.js 20+, Redis, FFmpeg

```bash
# 1. Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# 2. Start Redis (separate terminal)
redis-server

# 3. Start FastAPI (separate terminal)
uvicorn app.main:app --reload --port 8000

# 4. Start Celery Worker (separate terminal)
celery -A app.celery_app worker -Q siphon -l info -c 2

# 5. Start Celery Beat (separate terminal)
celery -A app.celery_app beat -l info

# 6. Frontend (separate terminal)
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173` on your phone (same WiFi) or desktop.

### Docker (One Command)

```bash
cd siphon
docker compose up -d
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Redis: `localhost:6379`

---

## Deploy to Render

**Is Render good? Yes — for prototyping and small-scale usage.**

- **Free tier**: Sleeps after 15 min inactivity. 512MB RAM. Good for testing.
- **Paid ($7/mo)**: Always-on. Good for personal use.
- **For production**: Use a $5/mo VPS (Hetzner, DigitalOcean) with Docker.

See [`DEPLOY.md`](DEPLOY.md) for full Render, VPS, and Docker deployment guides.

---

## Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Optional
DATABASE_URL=sqlite:///./siphon.db
PROXY_URL=http://proxy:8080
PROXY_URLS=http://proxy1:8080,http://proxy2:8080
ADMIN_TOKEN=your-secret-token
API_KEY=optional-access-key
ENABLE_BATCH=true
ENABLE_AUDIO_ONLY=true
ENABLE_WEBSOCKET=true
YTDLP_MAX_FILESIZE_MB=2048
LOG_FORMAT=json
```

---

## Screenshots (Mental Model)

### Step 1 — URL Input
- Logo with blue glow, URL input, Scan button, Audio/Batch toggles, install banner

### Step 2 — Resolution Select
- Grid of resolution buttons (360p, 480p, 720p, 1080p, 4K) with HD/SD badges

### Step 3 — Progress
- 4-step progress bar: In Queue → Extracting → Assembling → Ready
- Percentage bar, live status text, WebSocket or polling
- When done: "Save to Device" + Share + QR Code buttons

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, FastAPI, Celery, Redis, SQLite, SQLAlchemy |
| **Extraction** | Playwright (stealth), yt-dlp, FFmpeg |
| **Frontend** | Vite, React 18, TypeScript, Tailwind CSS |
| **PWA** | Web App Manifest, Service Worker, Vite PWA Plugin |
| **Queue** | Celery + Redis (concurrency limit: 2) |
| **Storage** | Local ephemeral `/temp/downloads/` (auto-cleaned) |
| **Deployment** | Docker, Docker Compose, Render, VPS |

---

## License

Private use only. Not for public redistribution.

---

Built with full creative control. Production-ready architecture.
