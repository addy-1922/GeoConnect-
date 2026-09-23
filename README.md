# 📍 GeoConnect — Real-Time Location Collaboration Platform

A production-style portfolio project: real-time location sharing, Discord-like
rooms, live map collaboration, real-time chat and notifications.

```text
Google Maps
      +
Real-Time Location Sharing
      +
Discord-like Rooms
      +
Real-Time Notifications
      +
Location-Based Collaboration
```

---

## Current Status — Complete ✅

All planned features are implemented and verified end-to-end across REST API,
WebSockets and the React UI.

### What works right now

| Piece | Status |
| --- | --- |
| React frontend (Vite) on http://localhost:5173 | ✅ |
| Django backend (ASGI/Daphne) on http://127.0.0.1:8080 | ✅ |
| REST API health endpoint `/api/health/` | ✅ |
| Register / Login / Logout, session auth + CSRF | ✅ |
| Profiles with status, avatar upload and live-location toggle | ✅ |
| Rooms, membership, roles (OWNER / ADMIN / MEMBER) | ✅ |
| Real-time chat via WebSockets | ✅ |
| Online / Away / Offline presence | ✅ |
| Geolocation sharing ON/OFF + last-known location | ✅ |
| Leaflet + OpenStreetMap live map | ✅ |
| Location events & map markers (live broadcast) | ✅ |
| Real-time notifications (REST + WebSocket push) | ✅ |
| Nearby users (haversine distances) | ✅ |
| Search (users, rooms, events, markers) | ✅ |
| PostgreSQL 17 — database `geoconnect` | ✅ |
| Redis — Memurai service on `127.0.0.1:6379` (channel layer + presence) | ✅ |
| Backend tests (72) and frontend tests (21) | ✅ |

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React (JavaScript), Vite, Leaflet, react-leaflet, HTML, CSS |
| Backend | Python, Django, Django REST Framework, Django Channels |
| Real-time | WebSockets (via Channels), Redis channel layer |
| Database | PostgreSQL |
| Cache / channel layer | Redis (Memurai on Windows) |
| Mapping | Leaflet + OpenStreetMap |
| Location | Browser Geolocation API |

No Node.js/Express on the backend — the backend is 100% Django.

---

## Architecture

```text
                 REACT FRONTEND  (http://localhost:5173)
                       │
             ┌─────────┴─────────┐
             │                   │
          REST API           WebSocket        (Vite proxy /api, /ws, /media)
             │                   │
             ▼                   ▼
       Django + DRF       Django Channels
             │                   │
             │                  Redis (Memurai)
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
                   PostgreSQL
```

### Project layout

```text
geo-connect/
│
├── backend/
│   ├── .venv/                        # Python virtual environment (not committed)
│   ├── .env                          # local environment variables (not committed)
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings.py               # PostgreSQL, Redis channel layer, DRF, CORS
│   │   ├── urls.py                   # /admin/, /api/...
│   │   ├── asgi.py                   # ASGI entry: http + websocket dispatch
│   │   ├── wsgi.py
│   │   └── routing.py                # WebSocket routes
│   ├── accounts/                     # auth, profiles, avatars
│   ├── rooms/                        # rooms, membership, roles, room socket
│   ├── messages/                     # chat (history + REST/socket send)
│   ├── locations/                    # sharing, markers, nearby (haversine)
│   ├── events/                       # location events
│   └── notifications/                # per-user inbox + push
│
├── frontend/
│   ├── vite.config.js                # dev server + /api, /ws, /media proxy → Django
│   ├── index.html
│   └── src/
│       ├── components/               # Navbar, MapView, ChatBox, MembersList, ...
│       ├── pages/                    # Login, Register, Dashboard, Profile, Room
│       ├── services/                 # api.js (REST client + CSRF), websocket.js
│       ├── hooks/                    # useGeolocation
│       ├── context/                  # AuthContext, NotificationsContext
│       ├── utils/                    # format helpers
│       ├── test/                     # Vitest setup
│       ├── App.jsx                   # routes + auth guards
│       ├── index.css
│       └── main.jsx
│
├── scripts/
│   ├── start-postgres.ps1            # starts local PostgreSQL (not a service)
│   ├── start-backend.ps1             # Django on 127.0.0.1:8080
│   └── start-frontend.ps1            # Vite on http://localhost:5173
│
├── .gitignore
├── .env.example
└── README.md
```

---

## Prerequisites

Already installed on this machine:

- Python **3.13.9**
- Node.js **24.x** / npm **12.x**
- PostgreSQL **17.11** (ZIP binaries at `C:\Users\hp\Tools\postgresql`)
- Redis-compatible **Memurai 4.1.2** (Windows service)

Notes:

- PostgreSQL was installed as a portable ZIP distribution (no admin, no Windows
  service). Start it with `scripts\start-postgres.ps1` (or re-run
  `pg_ctl -D <data> start`). It does **not** autostart after reboot.
- Memurai runs as a Windows service named `Memurai` and autostarts.

---

## Setup

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Copy `.env.example` from the repo root to `backend\.env` (already created for
you during setup), then adjust values if needed.

Run migrations (creates the Django tables in PostgreSQL):

```powershell
.venv\Scripts\python manage.py migrate
```

### 2. Frontend

```powershell
cd frontend
npm install
```

---

## Environment variables (`backend\.env`)

```env
SECRET_KEY=your_long_random_secret
DEBUG=True

DB_NAME=geoconnect
DB_USER=geo_connect
DB_PASSWORD=GeoConnect123
DB_HOST=127.0.0.1
DB_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/0

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

**Never commit `.env`.** A template lives at `.env.example`.

---

## How to run

Open three terminals (or use the scripts):

```powershell
# 1) Database: start PostgreSQL (if it isn't already running)
powershell -ExecutionPolicy Bypass -File scripts\start-postgres.ps1

# 2) Backend: Django on http://127.0.0.1:8080
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1

# 3) Frontend: React on http://localhost:5173
powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1
```

The Vite dev server proxies `/api` and `/ws` → `http://127.0.0.1:8080` and
`/media` for avatars, so the browser never calls Django directly during
development.

---

## Deploy to Render (free)

The repo includes a `render.yaml` Blueprint that provisions the **entire stack**
in one step: a Docker web service + managed Postgres + managed Redis-compatible
Key Value (all on the free tier, no credit card required).

1. Push the repo to GitHub (the Blueprint is read from the repo root).
2. In the Render dashboard: **New + → Blueprint** → connect the GitHub repo.
3. Render auto-creates `geoconnect` (web), `geoconnect-db` (Postgres) and
   `geoconnect-redis` (Key Value), wires `DATABASE_URL` and `REDIS_URL`
   automatically, and deploys. A live `https://geoconnect.onrender.com` URL is
   generated on success.
4. Optional first-time users: register two accounts in the browser and test a
   room, chat and live location.

How it works:

- `Dockerfile`: multi-stage — `node:20` builds the React app
  (`frontend/dist`), `python:3.13-slim` installs `backend/requirements.txt`,
  runs `migrate` + `collectstatic`, then launches **daphne** (ASGI, so WebSockets
  work) on `$PORT`.
- The SPA is served by Django via WhiteNoise (`WHITENOISE_ROOT` →
  `backend/frontend_dist`) with an SPA fallback route; `/api`, `/ws`, `/media`
  are never swallowed by the fallback.
- Env vars set by the Blueprint: `DEBUG=False`, `ALLOWED_HOSTS=*`,
  `SECRET_KEY` (auto-generated), `DATABASE_URL`, `REDIS_URL`.

Free-tier caveats:

- Web services **spin down after ~15 min idle** and take ~1 min to wake on the
  next request.
- Free Postgres **expires after 30 days** (upgrade or re-create to keep it).
- The web service filesystem is ephemeral — uploaded **avatars reset on every
  redeploy**. Attach a persistent disk (~1 GB) mounted at `backend/media` if you
  want uploads to survive redeploys.

---

## Verification

### Health check

`GET /api/health/` returns `{"status": "ok", "database": "connected", "redis": "connected", ...}`
via http://127.0.0.1:8080/api/health/ or the proxy at
http://localhost:5173/api/health/.

### API surface

| Endpoint | Purpose |
| --- | --- |
| `POST /api/auth/register/` `login/` `logout/`, `GET /api/auth/csrf/` | auth |
| `GET/PATCH /api/users/me/`, `GET /api/users/?search=` | profile & users |
| `GET/POST /api/rooms/`, `GET/PATCH/DELETE /api/rooms/<id>/` | rooms |
| `POST /api/rooms/<id>/join/` `leave/`, `GET/POST .../members/` | membership |
| `GET/POST .../messages/`, `events/`, `markers/`, `locations/`, `nearby/` | collaboration |
| `GET /api/notifications/`, `.../unread-count/`, `POST .../<id>/read/` | notifications |
| `GET /api/rooms/search/?q=` | global search |

### WebSocket endpoints

| Endpoint | Group | Frames |
| --- | --- | --- |
| `/ws/rooms/<id>/` | `room_<id>` | `room_snapshot`, `chat_message`, `user_joined`, `user_left`, `presence`, `event_created`, `marker_created` |
| `/ws/location/<id>/` | `location_room_<id>` | `location_update`, `location_shared`, `location_stopped` |
| `/ws/notifications/` | `user_<id>` | `notification` |

Auth model: a session cookie. The room and location sockets require the user
to be a room member; otherwise the connection is closed.

### Tests

Backend (SQLite in-memory + in-memory channel layer):

```powershell
cd backend
$env:PYTHONPATH = "<path-to-test-settings>;<backend-path>"
.venv\Scripts\python manage.py test --settings=test_settings
```

Frontend (Vitest + Testing Library):

```powershell
cd frontend
npm test          # 21 tests
npm run build     # production build
npm run lint      # oxlint
```

---

## Development credentials (local only)

| Resource | Username | Password |
| --- | --- | --- |
| PostgreSQL superuser | `postgres` | `GeoConnect123` |
| PostgreSQL app user | `geo_connect` | `GeoConnect123` |
| Django admin / superuser | `admin` | `GeoConnect123` |

These are development-only values for your local machine. Change them for anything public.

---

## Feature notes

- **Privacy first**: nobody can see your location unless you explicitly enable
  sharing. Only the last-known coordinate is stored (no history).
- **Roles**: OWNER of a room can promote/demote; ADMIN can manage members;
  MEMBER can participate. Higher roles cannot be changed by peers.
- **Marker types**: `meeting_point`, `danger`, `food`, `parking`, `important`, `custom`.
- **Profile statuses**: `online`, `away`, `offline`.