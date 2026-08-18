# my_money frontend

React + Vite + TypeScript. Runs as a regular web app, an installable PWA (mobile), and a native
macOS app via Tauri.

## Stack

- **React 19** + **TypeScript** + **Vite**
- **Tailwind CSS v4** — styling
- **TanStack Query** — server state / caching
- **React Router** — routing
- **axios** — HTTP client
- **vite-plugin-pwa** — installable PWA (manifest + service worker)
- **Tauri v2** — native macOS shell around the same web app

## Setup

```bash
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm install
```

The backend must be running (`docker compose up` from the repo root, or `uvicorn src.main:app --reload`).

## Commands

```bash
npm run dev          # dev server at http://localhost:5173
npm run build         # typecheck + production build to dist/
npm run preview       # serve the production build locally
npm run gen:api        # regenerate src/api/schema.d.ts from the backend's OpenAPI schema
                       # (backend must be running at VITE_API_BASE_URL)

npm run tauri dev      # native macOS window (requires Rust toolchain: https://rustup.rs)
npm run tauri build    # .app bundle in src-tauri/target/release/bundle/macos/
```

## Mobile (PWA)

Open the dev/preview URL from a phone on the same network (e.g. `http://<mac-lan-ip>:5173`) and
use the browser's "Add to Home Screen". Requires `APP_HOST=0.0.0.0` on the backend (already the
default) and the phone's origin to be reachable — CORS is currently open (`ALLOWED_ORIGINS=*`).

## Status

Only `/accounts` is wired up end-to-end — it's the only resource with an HTTP router on the
backend so far. Balances/Ledger pages are placeholders until those routers exist.
