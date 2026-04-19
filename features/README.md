# Features

實作目標的使用者故事。每個檔案描述一個完整情境：主要流程、UI 草稿、邊界條件、影響的元件。

| # | 情境 | 描述 |
|---|---|---|
| [01](01-explore-by-map.md) | Explore by Map | 在網頁地圖上點擊 teleport，探索遊戲中的花 |
| [02](02-walk-playback.md) | Walk Playback | 在地圖畫路徑播放模擬走路（GPX 匯入延後） |
| [03](03-shortcuts-crud.md) | Shortcuts CRUD | 在網頁收藏常去地點、匯出入 JSON 備份 |
| [04](04-cli-quick-teleport.md) | CLI Quick Teleport | 不開瀏覽器，terminal 一行快速傳送 |
| [05](05-phone-app-home.md) | Phone App Home | Mock GPS app 首頁顯示狀態、IP、當前位置 |
| [06](06-first-time-setup.md) | First-Time Setup | 朋友 clone repo 後從零跑起來的流程 |
| [07](07-auto-plant.md) | Auto Plant | 設定圓形範圍內掛機隨機走動，自動種花 |

## 架構前提

| 層 | 職責 |
|---|---|
| **Phone (Android app)** | **State owner**：locations 存 flat JSON。HTTP server：`POST /teleport`、`POST /stop`、`GET/PUT /locations`。Share intent target（接 Google Maps 分享） |
| **Web SPA (Svelte)** | UI 大本營：地圖、locations CRUD（透過 HTTP 打手機）、GPX 路徑播放。不自己存清單 |
| **CLI / TUI (Python)** | Stateless 遙控器：貼座標送、stop。不碰清單 |

**為什麼手機當 state owner：**
- 多台電腦同時看同一份清單
- 遊戲 → Google Maps → 分享到 Warp 能直接寫入清單（不需電腦在線）
- 單一真相來源，避免多 client 同步問題

**換手機備份**：透過網頁「匯出 JSON」下載；新手機匯入回去。（Phase 2 實作）
