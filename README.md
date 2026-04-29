# TeamDev X Terminal

<div align="center">

![TeamDev Terminal](https://img.shields.io/badge/TeamDev-Terminal-00ff9d?style=for-the-badge&logo=gnome-terminal&logoColor=black)
![Version](https://img.shields.io/badge/version-2.4.0-blue?style=for-the-badge)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A full-featured, browser-based Ubuntu 24.04 terminal — no SSH, no client install required.**  
Access a real PTY shell from any modern browser, with file uploads, PWA support, and one-click cloud deployment.

[Features](#-features) · [Quick Start](#-quick-start) · [Configuration](#-configuration) · [Deployment](#-deployment) · [Security](#-security)

</div>

---

## Overview

TeamDev X Terminal is a lightweight, self-hosted web terminal that exposes a real Linux PTY (pseudo-terminal) session over WebSocket. It runs entirely in Python's standard library — no heavy dependencies, no npm, no build step. The browser frontend is a single HTML file powered by [xterm.js](https://xtermjs.org/), giving you a pixel-perfect terminal experience with true 256-colour and truecolor support.

Originally built for quick cloud-hosted developer sandboxes, it deploys in seconds to Railway, Render, or any Docker-capable host.

---

## ✨ Features

### Terminal Engine
- **Real PTY shell** — spawns `/bin/bash` (or `$SHELL`) via `pty.fork()`, not a command pipe
- **Full xterm.js frontend** — proper escape sequences, colour, cursor control
- **Dynamic resize** — the PTY window size syncs with your browser window in real time
- **256-colour + truecolor** — `TERM=xterm-256color`, `COLORTERM=truecolor`
- **UTF-8 / locale aware** — `LANG=en_US.UTF-8`, `LC_ALL=en_US.UTF-8`
- **Ping / pong keepalive** — prevents idle WebSocket disconnections

### File Management
- **Drag-and-drop file upload** — files land in `/tmp/teamdev_uploads/` inside the container
- **Base64 upload over WebSocket** — works even behind restrictive proxies
- **REST upload endpoint** — `POST /upload` for programmatic use

### UI & UX
- **Dark cyberpunk theme** — JetBrains Mono, Orbitron, Share Tech Mono fonts; green-on-black aesthetic
- **Password-protected login screen** — configurable via environment variable
- **Sidebar with shortcuts** — common command shortcuts accessible from the toolbar
- **Live clock** in the title bar
- **PWA installable** — `manifest.json` + service worker icons; install to home screen on mobile or desktop

### Deployment
- **Zero Python dependencies** — `requirements.txt` is intentionally empty; uses only the standard library
- **Docker image** — based on `ubuntu:24.04`; includes bash, curl, wget, git, vim, nano, htop, python3, gcc, tmux, jq, and more
- **Docker Compose** — persistent volumes for uploads and bash history, health check included
- **Railway** — `railway.json` included for one-click deploy
- **Render** — `render.yaml` included for one-click deploy
- **Heroku / Procfile** — `web: python3 terminal_server.py`
- **Health check endpoint** — `GET /health` returns `200 OK` for load-balancer probes
- **Optional keepalive loop** — pings a URL every 25 seconds to prevent free-tier spin-down

---

## 📁 Project Structure

```
TeamDev-Terminal/
├── terminal_server.py        # WebSocket + HTTP server (pure stdlib Python)
├── teamdev_terminal_ui.html  # Single-file frontend (xterm.js, CSS, JS)
├── manifest.json             # PWA web app manifest
├── icon-192.png              # PWA icon (192×192)
├── icon-512.png              # PWA icon (512×512)
├── Dockerfile                # Ubuntu 24.04 image
├── docker-compose.yml        # Compose stack with volumes & health check
├── .env.example              # Environment variable template
├── .dockerignore             # Docker build exclusions
├── railway.json              # Railway deployment config
├── render.yaml               # Render deployment config
├── Procfile                  # Heroku / Procfile-based platform config
└── requirements.txt          # Empty — no pip dependencies
```

---

## 🚀 Quick Start

### Option 1 — Docker Compose (recommended)

```bash
# Clone / unzip the project
git clone https://github.com/your-org/teamdev-terminal.git
cd teamdev-terminal

# Copy and edit environment variables
cp .env.example .env
# Set TERMINAL_PASSWORD and optionally KEEPALIVE_URL in .env

# Build and run
docker compose up -d
```

Open **http://localhost:7681** in your browser.

---

### Option 2 — Docker (single container)

```bash
docker build -t teamdev-terminal .

docker run -d \
  -p 7681:7681 \
  -e TERMINAL_PASSWORD="YourSecurePassword" \
  -e PORT=7681 \
  --name teamdev-terminal \
  teamdev-terminal
```

---

### Option 3 — Run directly (Linux / macOS)

> Requires Python 3.8+ and a POSIX system (Linux or macOS). Windows is **not** supported (requires `pty` module).

```bash
cd TeamDev-Terminal

# Set your password
export TERMINAL_PASSWORD="YourSecurePassword"

# Optionally set the port (default: 7681)
export PORT=7681

python3 terminal_server.py
```

Open **http://localhost:7681** in your browser.

---

## ⚙️ Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and adjust as needed.

| Variable            | Default              | Description                                                                 |
|---------------------|----------------------|-----------------------------------------------------------------------------|
| `PORT`              | `7681`               | TCP port the server listens on                                              |
| `TERMINAL_PASSWORD` | `TeamDev@2026`       | Password required to access the terminal UI                                 |
| `KEEPALIVE_URL`     | *(empty)*            | If set, the server pings `<KEEPALIVE_URL>/health` every 25 s to prevent idle spin-down on free-tier hosts |
| `SHELL`             | `/bin/bash`          | Shell binary to spawn for PTY sessions                                      |

### `.env.example`

```dotenv
PORT=7681
KEEPALIVE_URL=https://your-app.onrender.com
```

> **Important:** Always change `TERMINAL_PASSWORD` before deploying to a public-facing host.

---

## 🌐 Deployment

### Railway

1. Push your project to a GitHub repository.
2. Create a new Railway project → **Deploy from GitHub repo**.
3. Set the `TERMINAL_PASSWORD` environment variable in Railway's dashboard.
4. Railway picks up `railway.json` automatically — no further configuration needed.

```json
// railway.json
{
  "deploy": {
    "startCommand": "python3 terminal_server.py",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

### Render

1. Connect your GitHub repository to Render.
2. Render reads `render.yaml` automatically.
3. Add `TERMINAL_PASSWORD` as an environment variable in the Render dashboard.

The `render.yaml` sets `PORT=10000` (Render's required port) and wires `KEEPALIVE_URL` to the service's own hostname.

---

### Heroku / Procfile platforms

```
web: python3 terminal_server.py
```

Set `PORT` (Heroku injects it automatically) and `TERMINAL_PASSWORD` via your platform's config vars.

---

### Docker Compose (production)

The included `docker-compose.yml` provides:

- Named volumes for uploads (`/tmp/teamdev_uploads`) and bash history
- Automatic container restart (`restart: always`)
- Health check via `curl /health`
- Structured JSON logging with rotation (10 MB × 3 files)

```bash
docker compose up -d          # start
docker compose logs -f        # stream logs
docker compose down           # stop
```

---

## 🔒 Security

> **This project is designed for personal developer sandboxes and trusted internal teams. Review these points carefully before exposing it to the internet.**

- **Password authentication** — the login screen requires `TERMINAL_PASSWORD`. Always set a strong, unique password.
- **Root / sudo access** — the Docker container grants passwordless `sudo` to simplify development workflows. This is intentional for a sandbox environment; do not use in multi-tenant production.
- **No TLS by default** — run behind a TLS-terminating reverse proxy (nginx, Caddy, Traefik) or use a platform that provides HTTPS automatically (Railway, Render).
- **Upload directory** — uploaded files go to `/tmp/teamdev_uploads/` inside the container. Bind a volume if persistence across restarts is needed.
- **Network exposure** — the server binds to `0.0.0.0`. Use firewall rules or a proxy to restrict access.

### Recommended production checklist

- [ ] Change `TERMINAL_PASSWORD` to a strong, unique value
- [ ] Enable HTTPS via a reverse proxy or cloud platform
- [ ] Restrict port 7681 at the firewall / security group level
- [ ] Review and harden `sudoers` if deploying for untrusted users

---

## 🛠️ Architecture

```
Browser
  │
  │  HTTP GET /          → serves teamdev_terminal_ui.html (with injected password)
  │  HTTP GET /health    → returns 200 OK
  │  HTTP POST /upload   → base64 file upload
  │  WS  ws://host/      → WebSocket terminal session
  │
  ▼
terminal_server.py  (pure Python, stdlib only)
  │
  ├── TermServer          raw TCP server, per-connection thread
  ├── handle_conn()       HTTP/WebSocket demux (upgrade detection)
  ├── handle_http()       static file + upload handler
  ├── PtySession          pty.fork() → bash, read loop → ws_json()
  └── ws_loop()           WebSocket message pump (input / resize / upload)
```

The server speaks raw TCP and implements the WebSocket handshake and framing protocol itself — there are no third-party server frameworks.

---

## 🖥️ Browser Compatibility

| Browser         | Supported |
|-----------------|-----------|
| Chrome / Edge   | ✅        |
| Firefox         | ✅        |
| Safari (macOS)  | ✅        |
| Safari (iOS)    | ✅        |
| Android Chrome  | ✅        |

PWA installation (Add to Home Screen) is supported on Chrome, Edge, and Android Chrome. Safari supports standalone mode but installation flow varies by iOS version.

---

## 🤝 Credits

- **Author / Maintainer:** [@MR_ARMAN_08](https://t.me/MR_ARMAN_08)
- **Community:** [TeamDevXBots](https://t.me/Team_X_Og) on Telegram
- **Terminal emulator:** [xterm.js](https://xtermjs.org/) (MIT)
- **Fonts:** JetBrains Mono, Orbitron, Share Tech Mono (Google Fonts)
- **Base image:** [Ubuntu 24.04 LTS](https://hub.docker.com/_/ubuntu)

---

## 📄 License

This project is released under the **MIT License**. See [LICENSE](./LICENSE) for full terms.
