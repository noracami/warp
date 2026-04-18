<script lang="ts">
  import { onMount } from "svelte";
  import type L from "leaflet";
  import Map from "./lib/Map.svelte";
  import { teleport, stopMock, getStatus } from "./lib/api";
  import { loadBaseUrl, saveBaseUrl } from "./lib/storage";

  const GAME_ZOOM = 17;

  const initialUrl = loadBaseUrl();
  let baseUrl = $state(initialUrl);
  let urlDraft = $state(initialUrl);
  let editing = $state(initialUrl === "");
  let marker = $state<[number, number] | null>(null);
  let pending = $state<[number, number] | null>(null);
  let connected = $state<boolean | null>(null);
  let busy = $state(false);
  let errorMessage = $state<string | null>(null);
  let mapInstance = $state<L.Map | null>(null);

  onMount(async () => {
    if (!baseUrl) return;
    try {
      const status = await getStatus(baseUrl);
      connected = true;
      if (status.running && status.lat != null && status.lng != null) {
        marker = [status.lat, status.lng];
      }
    } catch {
      // 啟動時連不到就算了，使用者點地圖時會再試
    }
  });

  function handleMapClick(lat: number, lng: number) {
    if (!baseUrl) {
      editing = true;
      errorMessage = "請先設定手機 URL";
      return;
    }
    errorMessage = null;
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

  async function handleStop() {
    if (!baseUrl) return;
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
    <button onclick={handleStop} disabled={busy || !baseUrl}>Stop mock</button>
  </header>

  <main class="main">
    <Map
      {marker}
      {pending}
      onMapClick={handleMapClick}
      onPendingCommit={commitPending}
      onReady={(m) => (mapInstance = m)}
    />

    {#if pending}
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

  .commit-bar {
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
</style>
