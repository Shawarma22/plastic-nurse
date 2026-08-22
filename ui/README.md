# The Face — Touchscreen UI

React + Vite + TypeScript frontend for the medical droid, driven against the
FastAPI service in `../core`. Built for a fullscreen Chromium kiosk on the
Raspberry Pi touchscreen (touch targets are ≥48×48px throughout).

## Setup

```bash
npm install
cp .env.example .env   # point VITE_API_BASE_URL at core if not localhost:8000
npm run dev
```

Default operator login (created by `core` on first boot): `admin` / `admin123`.

## Structure

- `src/api/client.ts` — fetch wrapper: attaches the JWT bearer token, normalizes errors.
- `src/api/endpoints.ts` — typed calls for every REST route in `core/app/routers/*.py`.
- `src/api/ws.ts` + `src/hooks/useWebSocketChannel.ts` — auto-reconnecting subscriptions to `/ws/state` and `/ws/telemetry`.
- `src/auth/` — token storage + `AuthContext`/`RequireAuth` route guard.
- `src/pages/` — one screen per subsystem: `VitalsPage`, `TeleopPage` (camera + drive), `DoorPage`.

## Notes

- Vitals display raw readings and calibration status only — no diagnostic
  labels, per the project's assistive-not-diagnostic rule.
- The camera `<img>` tag streams MJPEG from `/api/v1/camera/stream`, which
  accepts the JWT as a `?token=` query param since `<img>`/`<video>` can't
  set an `Authorization` header.
- Motor commands rely on the backend's watchdog auto-stop — the UI just
  re-issues a command on every press/tap rather than tracking hold state.

## Build

```bash
npm run build   # outputs to dist/, served by nginx or similar in kiosk mode
```
