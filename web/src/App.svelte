<script lang="ts">
  import { onMount } from "svelte";
  import type L from "leaflet";
  import Map from "./lib/Map.svelte";
  import { teleport, stopMock, getStatus } from "./lib/api";
  import { loadBaseUrl, saveBaseUrl } from "./lib/storage";
  import { distanceMeters, moveTowards, randomInCircle, type LatLng } from "./lib/geo";

  const GAME_ZOOM = 17;
  const CIRCLE_RADIUS_M = 300;
  const SPEED_MPS = 4.44; // 16 km/h
  const TICK_MS = 1000;
  const STEP_M = SPEED_MPS * (TICK_MS / 1000);
  const TRAIL_MAX = 200;

  type PlantMode = "idle" | "arming" | "configured" | "running";

  const initialUrl = loadBaseUrl();
  let baseUrl = $state(initialUrl);
  let urlDraft = $state(initialUrl);
  let editing = $state(initialUrl === "");
  let marker = $state<LatLng | null>(null);
  let pending = $state<LatLng | null>(null);
  let connected = $state<boolean | null>(null);
  let mockReady = $state<boolean | null>(null);
  let busy = $state(false);
  let errorMessage = $state<string | null>(null);
  let mapInstance = $state<L.Map | null>(null);

  let plantMode = $state<PlantMode>("idle");
  let circleCenter = $state<LatLng | null>(null);
  let plantStats = $state<{ steps: number; distanceM: number; startedAt: number } | null>(null);
  let trail = $state<LatLng[]>([]);
  let plantTimer: number | null = null;
  let plantTarget: LatLng | null = null;

  let circle = $derived(
    circleCenter
      ? { center: circleCenter, radius: CIRCLE_RADIUS_M, active: plantMode === "running" }
      : null,
  );

  async function refreshStatus() {
    if (!baseUrl) return;
    try {
      const status = await getStatus(baseUrl);
      connected = true;
      mockReady = status.mockReady ?? null;
      if (status.running && status.lat != null && status.lng != null && !marker) {
        marker = [status.lat, status.lng];
      }
    } catch {
      // ignore; 下次操作會再試
    }
  }

  onMount(() => {
    refreshStatus();
    const onFocus = () => refreshStatus();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  });

  function handleMapClick(lat: number, lng: number) {
    if (!baseUrl) {
      editing = true;
      errorMessage = "請先設定手機 URL";
      return;
    }
    errorMessage = null;
    if (plantMode === "arming") {
      circleCenter = [lat, lng];
      plantMode = "configured";
      return;
    }
    if (plantMode === "configured") {
      circleCenter = [lat, lng];
      return;
    }
    if (plantMode === "running") {
      return;
    }
    pending = [lat, lng];
  }

  async function commitPending() {
    if (!pending || !baseUrl) return;
    const [lat, lng] = pending;
    busy = true;
    errorMessage = null;
    try {
      await teleport(baseUrl, lat, lng);
      marker = [lat, lng];
      pending = null;
      connected = true;
    } catch (e) {
      connected = false;
      errorMessage = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  function cancelPending() {
    pending = null;
  }

  function enterArming() {
    pending = null;
    plantMode = "arming";
  }

  function cancelPlantSession() {
    stopPlantingLoop();
    plantMode = "idle";
    circleCenter = null;
    plantStats = null;
    plantTarget = null;
    trail = [];
  }

  function startPlantingLoop() {
    if (!circleCenter || !baseUrl) return;
    plantMode = "running";
    plantStats = { steps: 0, distanceM: 0, startedAt: Date.now() };
    plantTarget = null;
    trail = [];
    if (plantTimer != null) clearInterval(plantTimer);
    plantTimer = window.setInterval(tick, TICK_MS);
    tick();
  }

  function stopPlantingLoop() {
    if (plantTimer != null) {
      clearInterval(plantTimer);
      plantTimer = null;
    }
    if (plantMode === "running") plantMode = "configured";
  }

  function tick() {
    if (!circleCenter || !baseUrl) return;
    const current: LatLng = marker ?? circleCenter;
    if (!plantTarget || distanceMeters(current, plantTarget) <= STEP_M) {
      plantTarget = randomInCircle(circleCenter, CIRCLE_RADIUS_M);
    }
    const next = moveTowards(current, plantTarget, STEP_M);
    const stepDist = distanceMeters(current, next);
    marker = next;
    trail = [...trail, next].slice(-TRAIL_MAX);
    if (plantStats) {
      plantStats = {
        steps: plantStats.steps + 1,
        distanceM: plantStats.distanceM + stepDist,
        startedAt: plantStats.startedAt,
      };
    }
    teleport(baseUrl, next[0], next[1])
      .then(() => {
        connected = true;
      })
      .catch((e) => {
        connected = false;
        console.error("auto plant teleport failed", e);
      });
  }

  function formatElapsed(ms: number): string {
    const total = Math.max(0, Math.floor(ms / 1000));
    const mm = Math.floor(total / 60);
    const ss = total % 60;
    return `${mm}:${ss.toString().padStart(2, "0")}`;
  }

  async function handleStop() {
    if (!baseUrl) return;
    cancelPlantSession();
    busy = true;
    errorMessage = null;
    try {
      await stopMock(baseUrl);
      marker = null;
      connected = true;
    } catch (e) {
      connected = false;
      errorMessage = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  function commitUrl() {
    const trimmed = urlDraft.trim();
    if (!trimmed) return;
    baseUrl = trimmed;
    saveBaseUrl(trimmed);
    editing = false;
    connected = null;
  }

  function editUrl() {
    urlDraft = baseUrl;
    editing = true;
  }

  function dismissError() {
    errorMessage = null;
  }

  function zoomToGame() {
    if (!mapInstance) return;
    if (marker) {
      mapInstance.setView(marker, GAME_ZOOM);
    } else {
      mapInstance.setZoom(GAME_ZOOM);
    }
  }
</script>

<div class="app">
  <header class="bar">
    <div class="title">Warp</div>

    <div class="spacer"></div>

    <div class="status" data-state={connected === true ? "ok" : connected === false ? "err" : "idle"}>
      {#if connected === true}● Connected
      {:else if connected === false}○ Disconnected
      {:else}○ Idle{/if}
    </div>

    {#if editing}
      <input
        class="url-input"
        type="text"
        placeholder="http://192.168.1.42:8080"
        bind:value={urlDraft}
        onkeydown={(e) => {
          if (e.key === "Enter") commitUrl();
          if (e.key === "Escape" && baseUrl) editing = false;
        }}
      />
      <button onclick={commitUrl} disabled={!urlDraft.trim()}>Save</button>
    {:else}
      <button class="url-button" onclick={editUrl} title="Click to edit">
        {baseUrl}
      </button>
    {/if}

    <button onclick={zoomToGame} title="跳到遊戲縮放等級（zoom {GAME_ZOOM}）">🎯 Game zoom</button>
    <button
      onclick={enterArming}
      disabled={!baseUrl || plantMode === "arming" || plantMode === "running"}
      title="在圓形範圍內隨機走動自動種花"
    >
      🌸 Auto plant
    </button>
    <button onclick={handleStop} disabled={busy || !baseUrl}>Stop mock</button>
  </header>

  <main class="main">
    <Map
      {marker}
      {pending}
      {circle}
      {trail}
      onMapClick={handleMapClick}
      onPendingCommit={commitPending}
      onReady={(m) => (mapInstance = m)}
    />

    {#if mockReady === false}
      <div class="mock-warning" role="alert">
        <div class="mock-warning-title">⚠️ App 未被選為 mock provider</div>
        <div class="mock-warning-body">
          網頁操作不會影響遊戲。到 Android：<br />
          <b>設定 → 系統 → 開發者選項 → 選取模擬位置的應用程式 → Warp Mock GPS</b>
        </div>
        <button onclick={refreshStatus}>重新檢查</button>
      </div>
    {/if}

    {#if plantMode === "arming"}
      <div class="auto-bar">
        <span>🎯 點地圖設定圓心（半徑 {CIRCLE_RADIUS_M} m）</span>
        <button onclick={cancelPlantSession}>× Cancel</button>
      </div>
    {:else if plantMode === "configured" && circleCenter}
      <div class="auto-bar">
        <span class="coords">{circleCenter[0].toFixed(5)}, {circleCenter[1].toFixed(5)}</span>
        <span class="dim">· {CIRCLE_RADIUS_M} m</span>
        <button class="primary" onclick={startPlantingLoop}>▶ Start</button>
        <button onclick={cancelPlantSession}>× Cancel</button>
      </div>
    {:else if plantMode === "running" && plantStats}
      <div class="auto-bar running">
        <span>🌸 Running</span>
        <span class="dim">· {plantStats.steps} steps</span>
        <span class="dim">· {Math.round(plantStats.distanceM)} m</span>
        <span class="dim">· {formatElapsed(Date.now() - plantStats.startedAt)}</span>
        <button onclick={stopPlantingLoop}>⏹ Stop</button>
      </div>
    {:else if pending}
      <div class="commit-bar">
        <span class="coords">
          {pending[0].toFixed(5)}, {pending[1].toFixed(5)}
        </span>
        <button class="primary" onclick={commitPending} disabled={busy}>
          {busy ? "傳送中…" : "✓ Teleport"}
        </button>
        <button onclick={cancelPending} disabled={busy}>× Cancel</button>
      </div>
    {/if}
  </main>

  {#if errorMessage}
    <div class="toast" role="alert">
      <span>{errorMessage}</span>
      <button onclick={dismissError} aria-label="Dismiss">×</button>
    </div>
  {/if}
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    background: #0f1116;
    color: #e5e7eb;
    font-family:
      system-ui,
      -apple-system,
      "Segoe UI",
      sans-serif;
  }

  .bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #1a1d24;
    border-bottom: 1px solid #2a2d35;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
    z-index: 1000;
    position: relative;
    flex-wrap: wrap;
  }

  .title {
    font-weight: 700;
    font-size: 18px;
    letter-spacing: 0.5px;
    color: #f3f4f6;
  }

  .spacer {
    flex: 1;
  }

  .status {
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    padding: 4px 8px;
    border-radius: 4px;
  }

  .status[data-state="ok"] {
    color: #4ade80;
    background: rgba(34, 197, 94, 0.12);
  }

  .status[data-state="err"] {
    color: #fca5a5;
    background: rgba(239, 68, 68, 0.12);
  }

  .status[data-state="idle"] {
    color: #9ca3af;
    background: rgba(156, 163, 175, 0.08);
  }

  .url-input {
    padding: 6px 10px;
    font-size: 13px;
    font-family: ui-monospace, monospace;
    border: 1px solid #2a2d35;
    background: #0f1116;
    color: #e5e7eb;
    border-radius: 4px;
    min-width: 220px;
  }

  .url-input:focus {
    outline: none;
    border-color: #4b5563;
  }

  .url-button {
    background: #0f1116;
    border: 1px solid #2a2d35;
    padding: 6px 10px;
    font-size: 13px;
    font-family: ui-monospace, monospace;
    border-radius: 4px;
    cursor: pointer;
    color: #d1d5db;
  }

  .url-button:hover {
    background: #2a2d35;
    color: #f3f4f6;
  }

  button {
    padding: 6px 12px;
    font-size: 13px;
    border: 1px solid #2a2d35;
    background: #1a1d24;
    color: #e5e7eb;
    border-radius: 4px;
    cursor: pointer;
  }

  button:hover:not(:disabled) {
    background: #2a2d35;
  }

  button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .main {
    flex: 1;
    position: relative;
    min-height: 0;
  }

  .toast {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    padding: 10px 14px;
    background: rgba(69, 10, 10, 0.95);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 6px;
    font-size: 13px;
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  }

  .toast button {
    padding: 0 6px;
    border: none;
    background: transparent;
    font-size: 18px;
    line-height: 1;
    color: inherit;
    cursor: pointer;
  }

  .toast button:hover:not(:disabled) {
    background: rgba(239, 68, 68, 0.2);
  }

  .commit-bar,
  .auto-bar {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    padding: 8px 10px 8px 14px;
    background: rgba(26, 29, 36, 0.95);
    color: #e5e7eb;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    font-size: 13px;
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(6px);
  }

  .commit-bar .coords {
    font-family: ui-monospace, monospace;
    color: #fde047;
    padding-right: 6px;
  }

  .commit-bar button.primary {
    background: #facc15;
    color: #1a1d24;
    border-color: #eab308;
    font-weight: 600;
  }

  .commit-bar button.primary:hover:not(:disabled) {
    background: #eab308;
  }

  .auto-bar .coords {
    font-family: ui-monospace, monospace;
    color: #86efac;
  }

  .auto-bar .dim {
    color: #9ca3af;
    font-variant-numeric: tabular-nums;
  }

  .auto-bar button.primary {
    background: #22c55e;
    color: #052e16;
    border-color: #16a34a;
    font-weight: 600;
  }

  .auto-bar button.primary:hover:not(:disabled) {
    background: #16a34a;
  }

  .auto-bar.running {
    border-color: rgba(34, 197, 94, 0.5);
    box-shadow:
      0 6px 20px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(34, 197, 94, 0.2);
  }

  .mock-warning {
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    max-width: 520px;
    padding: 12px 16px;
    background: rgba(120, 53, 15, 0.95);
    color: #fde68a;
    border: 1px solid rgba(245, 158, 11, 0.6);
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.5;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  }

  .mock-warning-title {
    font-weight: 700;
    font-size: 14px;
    color: #fef3c7;
  }

  .mock-warning-body b {
    color: #fef3c7;
  }

  .mock-warning button {
    align-self: flex-start;
    background: rgba(245, 158, 11, 0.2);
    border-color: rgba(245, 158, 11, 0.6);
    color: #fef3c7;
  }

  .mock-warning button:hover:not(:disabled) {
    background: rgba(245, 158, 11, 0.3);
  }
</style>
