# 01 · Explore by Map

## 狀態
✅ **已實作於 commit `2d81f96`**（2026-04-19）。此文件反映**實際實作狀態**，非原始構想。後續改進項目見 `~/.claude/projects/.../memory/project_deferred_work.md`。

## 目標
玩家坐電腦前玩目標遊戲，用網頁地圖**點擊 → 預覽 → commit** 的方式 teleport，探索附近的花。這是**主要使用情境**。

## Actor
玩家（電腦 + 手機同時在手邊）

## 前提條件
- Mock GPS app 已在手機背景運行（`● Running` 或 `○ Waiting`）
- 電腦開 warp 網頁，已填入手機 URL（`http://<ip>:8080`）
- 手機前景是目標遊戲

## 主要流程
1. 網頁載入 → Map center / zoom 從 `localStorage` 還原
2. 同時打 `GET /status`；若 `running=true`，**紅點**直接落回當下 mock 座標（Source of truth = 手機）
3. 玩家在地圖別處點一下 → **黃色 pending pin（pulse 動畫）** 出現
4. 底部浮起 commit bar：座標 + `✓ Teleport` 主按鈕 + `× Cancel`
5. commit 有兩種入口：
   - 按 `✓ Teleport` 按鈕
   - **按黃點本身**（`cursor: pointer`）
6. commit 成功 → `POST /teleport` → 黃點消失 → 紅點移到新位置（optimistic）→ 遊戲 0.1 秒內看到新位置
7. 想換位置：點地圖別處 → 黃點搬移、bar 座標同步更新（不 commit）
8. 想取消：按 `× Cancel` → 黃點消失
9. 按 `🎯 Game zoom` → 飛到紅點並 zoom 17（對齊遊戲縮放等級）
10. 按 `Stop mock` → 紅點消失、手機回 Waiting（真實 GPS 恢復作用）

## UI 草稿（實作版）
```
┌── Warp · [●Connected/○Idle/○Disconn] · [http://...] · 🎯 Game zoom · Stop mock ──┐
│                                                                                   │
│   [+] zoom                                                                        │
│   [-]                                                                             │
│                                                                                   │
│                     [Leaflet map · Carto Dark tiles]                              │
│                                                                                   │
│                🟡  pending pin (pulse animation)                                  │
│                🔴  red pin (current mock location)                                │
│                                                                                   │
│            ┌─ 35.68000, 139.69000 · [✓ Teleport] [× Cancel] ─┐                   │
│            └───────────────────────────────────────────────────┘                 │
│                                               © OSM © CARTO · Leaflet            │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## 實作決策（從原本的 open questions 收斂）

### 1. 「目前位置」的 source of truth → 混合
- **啟動時**：`GET /status` 取手機當前 mock 座標（source of truth = 手機）
- **commit 之後**：立即 optimistic 更新紅點（不等再次 `/status` 確認）
- 原 spec 說 MVP 用 (a) optimistic，實際擴充成啟動時也回讀，讓重整頁面不會遺失紅點

### 2. 點擊立即 teleport → 改為 **preview + commit**
- 原因：使用者反映「有時會無意識點擊」
- 多了一層黃色 pending pin（pulse）作為視覺「這還沒 commit」的提示
- 三種 commit 入口讓老手也能快（`✓` 按鈕 / 按黃點）

### 3. 經度 wrap 處理（bug fix）
- Leaflet 水平捲動會產 `lng > 180` 或 `< -180`
- 無效經度送到 Android，FLP 會判定不合理 → 回退真實 Wi-Fi 位置（看起來像「沒動」）
- 解法：送出前用 `e.latlng.wrap()` 正規化到 `[-180, 180]`

### 4. 地圖樣式 → Carto **Dark**（非原本提的 Positron Light）
- 使用者偏好深色
- 同樣輕量、免費、非商用授權 OK

## 非目標（MVP 不做）
- **鍵盤 shortcut**：全部操作以滑鼠 / 觸控為主
- 地圖上 hover 顯示詳細資訊、圖層切換（衛星 / 街景）
- 「最近 N 個 teleport 歷史」trail 線（未實作，使用者未特別要求）

## 已知限制（**實作現況**，非 bug，已列入 deferred）
- **`connected` 狀態不主動偵測**：只反映「最後一次 HTTP 請求的結果」。手機斷網 30 秒後網頁仍顯示 Connected 直到下次操作。改善：deferred 項目 9（每 10s poll `/status`）
- **`/teleport` 回 200 不保證 mock 真的生效**：若手機 app 未被選為 mock provider，`setTestProviderLocation` 會 silent 失敗但 HTTP 仍回 200。改善：deferred 項目 5（server 端用 `getLastKnownLocation` echo 驗證）
- **紅點是 optimistic + 啟動快照**：不會主動反映 mock 被其他管道停掉（例如 phone app 重啟、另一個網頁 tab 按 Stop mock）

## 影響的元件
- **Web**（已實作）：
  - `src/lib/Map.svelte` — Leaflet、Carto Dark tiles、紅 / 黃 marker 雙層、點擊 + commit handler
  - `src/lib/api.ts` — `teleport` / `stopMock` / `getStatus`
  - `src/lib/storage.ts` — localStorage 存 baseUrl、mapView
  - `src/App.svelte` — 頂部 bar（狀態 / URL / Game zoom / Stop mock）、commit bar、state 機
- **Phone**（已實作於 commit `9df4030`）：`POST /teleport`、`POST /stop`、`GET /status`（NanoHTTPD）
