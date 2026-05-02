# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

Warp is a personal-use Mock GPS tool: an Android app on the phone exposes a small HTTP server, and a Svelte web app on the desk computer drives it. Used to teleport the phone's GPS while playing a location-based game.

Three components, each with its own role:

| Tier | Path | Role |
|---|---|---|
| Phone (Android, Kotlin) | `android/` | **State owner.** Foreground service runs `LocationManager` test providers + NanoHTTPD on port 8080. |
| Web SPA (Svelte 5 + Vite + Leaflet) | `web/` | Main UI. Map click → `POST /teleport`. Auto-plant random walk loop. |
| Python CLI/TUI | `main.py`, `tui.py` | Stateless remote. **Currently broken** — still on the deprecated ADB-broadcast transport. |

Current migration state: ADB broadcast was removed (commit `4c84607`). Phone now speaks HTTP only. The Python CLI/TUI has not yet been ported to HTTP — assume it does not run until "Phase 1b" in `features/` lands.

## Common commands

### Web (run from `web/`)
```bash
pnpm dev          # Vite dev server, default http://localhost:5173
pnpm build        # production build → dist/
pnpm check        # svelte-check + tsc
```

### Android (run from `android/`)
```bash
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb logcat -s MockLocationService WarpHttpServer   # tail server logs
```
Toolchain: JDK 17, `compileSdk = 35`, `minSdk = 29`. Single dependency outside AndroidX/Material is `org.nanohttpd:nanohttpd:2.3.1`.

### Python (root)
```bash
uv sync                                # set up .venv
uv run gps <command>                   # entry point — currently non-functional, see migration note
```

## Architecture notes worth knowing before editing

### HTTP contract (the only contract between tiers)
The phone exposes:
- `POST /teleport` — body `{"lat": float, "lng": float}`. Starts/updates the foreground service which pushes to both `gps` and `network` test providers every 500 ms.
- `POST /stop` — stops pushing; service stays alive.
- `GET /status` — `{ running, mockReady, lat, lng, lastTeleportAt }`. Side effect: calls `retrySetupIfNeeded()`, so a fresh `/status` after the user toggles the mock-provider setting re-arms the service without restart.

All responses include permissive CORS so the web SPA can hit the phone directly from a browser. Defined in `android/app/src/main/java/dev/warp/mockgps/HttpServer.kt`.

### `mockReady` is load-bearing
`MockLocationService` checks `AppOpsManager.OPSTR_MOCK_LOCATION` to detect whether the user has selected this app under "Select mock location app" in developer options. If not, `setTestProviderLocation` silently no-ops — `/teleport` returns 200 but nothing happens. The web app surfaces this as a yellow banner driven by `status.mockReady`. When changing teleport flow, preserve this signal.

### Service lifecycle
`MockLocationService` is the long-lived foreground service. It owns:
- The HTTP server (`HttpServer`) — started in `onCreate`.
- Test providers (`gps`, `network`) — set up via `addTestProvider` in `setupProviders()`.
- A 500 ms `Handler` loop pushing the current location.

State (`isRunning`, `currentLocation`, `lastTeleportAt`, `mockReady`) lives on the companion object so `MainActivity` and `HttpServer` can read it without binding. This means **state is lost if the service is killed** — there is no SharedPreferences persistence yet (deferred).

### Web state model
`web/src/App.svelte` is the controller. Key states:
- `pending` (yellow pin) → `marker` (red pin) on commit. Click-to-teleport was deliberately replaced with click-to-preview + commit.
- Coordinates are wrapped via `e.latlng.wrap()` before sending — Leaflet's horizontal scroll otherwise produces `lng > 180` which the Android `FusedLocationProvider` rejects, falling back to real Wi-Fi position.
- `mockReady === false` shows a warning banner; `window` focus event triggers `refreshStatus()` to re-check after the user fixes settings.
- Auto-plant mode (Feature 07): user picks a circle center, the loop ticks every 1 s, picks random target inside 300 m radius, walks at 4.44 m/s.

`web/src/lib/api.ts` is the single HTTP wrapper — keep all phone communication going through it.

### What's deliberately not abstracted
- Locations are **not** stored on the phone yet. The web app has no persistent shortcuts list. The architecture in `features/README.md` plans for `GET/PUT /locations` on the phone, but it's not implemented.
- The Python tier is broken. Don't fix it as a side quest — it needs a deliberate rewrite from ADB shell-out to `urllib`/`httpx` HTTP calls. Tracked in deferred work.

## When working in this repo

- The `features/` directory holds user-story specs that mix "design intent" with "actual implementation status." Each file's `## 狀態` section is the source of truth; don't take the rest as reflecting current code without checking.
- `locations.yaml` is gitignored and contains real coordinates; `locations.example.yaml` is the template.
- No test suite, no CI. Verify changes by building and exercising the path manually.
- README is in 繁體中文 and includes a migration banner warning that the Python CLI is broken — keep that banner accurate if you change the migration state.
