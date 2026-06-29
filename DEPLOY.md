# Siphon — Deployment Guide

## Is Render Good?

**Yes — Render is excellent for Siphon.** Here's the honest breakdown:

| Aspect | Render | Better Alternatives |
|--------|--------|---------------------|
| **Free Tier** | Web service sleeps after 15 min inactivity. 512MB RAM. 100GB egress. | **Fly.io** (free stays awake, 256MB shared), **Railway** ($5/mo credit) |
| **Always-On** | $7/mo web service | **Hetzner Cloud** ($5/mo VPS, 4x the power), **DigitalOcean** ($6/mo) |
| **Redis** | Redis Cloud (free 30MB) or Upstash (free 10K req/day) | Self-hosted Redis on same VPS |
| **SSL** | Automatic | Same |
| **Custom Domain** | Yes, free | Same |
| **Disk** | Ephemeral (resets on deploy) | Same on most platforms |
| **FFmpeg** | Must use Docker | Same everywhere |

**Verdict:** Use Render for prototyping and small-scale usage. If you need high-volume downloads (10+ per hour), move to a $5-10/mo VPS (Hetzner, DigitalOcean, Linode) with Docker.

---

## Deploy on Render (Free Tier)

### 1. Create a Web Service
- Go to [render.com](https://render.com) → New Web Service
- Connect your GitHub repo (or use Blueprint below)

### 2. Render Blueprint (`render.yaml`)

```yaml
services:
  - type: web
    name: siphon-backend
    env: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    envVars:
      - key: REDIS_URL
        fromService:
          type: redis
          name: siphon-redis
          property: connectionString
      - key: CELERY_BROKER_URL
        fromService:
          type: redis
          name: siphon-redis
          property: connectionString
      - key: CELERY_RESULT_BACKEND
        fromService:
          type: redis
          name: siphon-redis
          property: connectionString
      - key: TEMP_DOWNLOAD_DIR
        value: /tmp/siphon-downloads
      - key: DATABASE_URL
        value: sqlite:///tmp/siphon.db
      - key: YTDLP_MAX_FILESIZE_MB
        value: 512
    disk:
      name: siphon-data
      mountPath: /tmp/siphon-downloads
      sizeGB: 1

  - type: worker
    name: siphon-worker
    env: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    envVars:
      - key: REDIS_URL
        fromService:
          type: redis
          name: siphon-redis
          property: connectionString
      - key: CELERY_BROKER_URL
        fromService:
          type: redis
          name: siphon-redis
          property: connectionString
      - key: CELERY_RESULT_BACKEND
        fromService:
          type: redis
          name: siphon-redis
          property: connectionString
    disk:
      name: siphon-data
      mountPath: /tmp/siphon-downloads
      sizeGB: 1

  - type: static
    name: siphon-frontend
    buildCommand: cd frontend && npm install && npm run build
    publishPath: ./frontend/dist
    envVars:
      - key: VITE_API_URL
        value: https://siphon-backend.onrender.com
```

### 3. Create Redis Service on Render
- New → Redis → `siphon-redis` → Free plan
- Copy the `Internal Redis URL` → paste as `REDIS_URL` env var

### 4. Important: Docker File for Render

Render's free tier needs a lighter Dockerfile. Update `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install FFmpeg only (skip Playwright deps for lightweight deploy)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright install (may be slow on free tier, comment out if not needed)
# RUN playwright install chromium

COPY . .
RUN mkdir -p /tmp/siphon-downloads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Note:** On Render's free tier, Playwright browser installation is slow and memory-intensive. For lightweight sites, yt-dlp alone may work. For JavaScript-heavy sites, you need Playwright + a paid plan (1GB+ RAM).

---

## Deploy on Hetzner/DigitalOcean VPS (Best Value)

```bash
# 1. Provision a $5-6/mo Ubuntu 22.04 VPS
# 2. SSH in and run:

sudo apt update && sudo apt install -y docker.io docker-compose ffmpeg
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Logout and login again

git clone https://github.com/yourname/siphon.git
cd siphon
docker compose up -d
```

Add HTTPS with Caddy (auto SSL):

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

Create `Caddyfile`:
```
your-domain.com {
    reverse_proxy localhost:8000
}
```

```bash
sudo caddy start
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string |
| `CELERY_BROKER_URL` | Yes | - | Celery broker |
| `CELERY_RESULT_BACKEND` | Yes | - | Celery result backend |
| `DATABASE_URL` | No | `sqlite:///./siphon.db` | SQLite or PostgreSQL |
| `TEMP_DOWNLOAD_DIR` | No | `./temp/downloads` | Ephemeral file storage |
| `PROXY_URL` | No | - | Single proxy |
| `PROXY_URLS` | No | - | Comma-separated proxy list for rotation |
| `ADMIN_TOKEN` | No | - | Protects admin endpoints |
| `API_KEY` | No | - | Optional API key gate |
| `YTDLP_MAX_FILESIZE_MB` | No | 2048 | Max download size |
| `ENABLE_BATCH` | No | true | Enable batch downloads |
| `ENABLE_AUDIO_ONLY` | No | true | Enable audio extraction |
| `ENABLE_WEBSOCKET` | No | true | Enable real-time WebSocket |
| `LOG_LEVEL` | No | INFO | DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | No | json | json or text |

---

## Monitoring & Admin

### Health Dashboard
```bash
curl https://your-domain.com/api/admin/health
```

Returns real-time status of Redis, Celery workers, FFmpeg, Playwright, yt-dlp, and proxy pool.

### Stats (requires `ADMIN_TOKEN`)
```bash
curl "https://your-domain.com/api/admin/stats?token=YOUR_ADMIN_TOKEN"
```

### Force Cleanup
```bash
curl -X POST "https://your-domain.com/api/admin/cleanup?token=YOUR_ADMIN_TOKEN"
```

---

## PWA Install Notes

### iOS Safari
- Must be served over **HTTPS** (Render provides this automatically)
- Tap Share → Add to Home Screen
- The install banner auto-detects and shows instructions

### Android Chrome
- Install banner appears automatically when criteria met (HTTPS, manifest, service worker, 512x512 icon)
- One tap to install

### Windows/macOS (Chrome/Edge)
- Address bar shows install icon
- Or: Chrome menu → Install Siphon...

---

## Limitations & Recommendations

1. **Disk Space**: Downloads are ephemeral. On Render free tier, disk resets on deploy. Use a paid plan with persistent disk or a VPS.
2. **Memory**: Playwright + FFmpeg + yt-dlp need ~1GB RAM. Free tier (512MB) may OOM. Use a $7/mo Render plan or $5/mo VPS.
3. **Timeouts**: Free tier web services have 100-second request timeout. Downloads run in background Celery tasks, so this is fine.
4. **Rate Limits**: Add `ADMIN_TOKEN` and configure `RATE_LIMIT_*` env vars to prevent abuse.
5. **Proxy**: For Cloudflare-protected sites, configure `PROXY_URLS` with residential proxies.

---

## Quick Start Checklist

- [ ] Clone repo, install backend deps (`pip install -r requirements.txt`)
- [ ] Install Playwright browsers (`playwright install chromium`)
- [ ] Install FFmpeg (`sudo apt install ffmpeg` or `brew install ffmpeg`)
- [ ] Start Redis (`redis-server` or Docker)
- [ ] Start backend (`uvicorn app.main:app --reload`)
- [ ] Start Celery worker (`celery -A app.celery_app worker -Q siphon -c 2`)
- [ ] Start Celery beat (`celery -A app.celery_app beat`)
- [ ] Install frontend deps (`npm install`)
- [ ] Start frontend (`npm run dev`)
- [ ] Open `http://localhost:5173` on your phone
- [ ] Deploy to Render or VPS for public access
