# 02 · Walk Playback

## 目標
在地圖上畫路徑（依序點擊），模擬連續走路。在網頁端控制播放速度 / 暫停 / 跳段。

## Actor
玩家（長時間掛機，或想走一段路看沿途變化）

## 前提條件
- 基礎 teleport 能用
- 有地圖

## 主要流程

### (1) 在地圖畫路徑（**優先實作**）
1. 按「Draw path」進入模式
2. 地圖依序點擊 waypoints（至少 2 個）
3. 每點一下，地圖連出一條折線 + 小圓點
4. 可拖曳既有點調整、點右鍵刪點
5. 按「Done」→ 路徑完成 → 開啟播放控制面板

### (2) 播放
1. 設定 speed（公尺/秒）、interval（送頻率）
2. 按 ▶ → 網頁 `setInterval` 定時 `POST /teleport`
3. 網頁依據 speed 插值計算當下座標（兩個 waypoint 間線性分割）
4. 進度條 + 當前 waypoint 高亮
5. 可暫停 / 調速 / 跳過 waypoint / 停止

### (3) 路徑儲存（可選）
- 存進「我的路徑」清單（單獨一張表，不和 locations 混）
- 格式：`{name, waypoints: [[lat, lng], ...], created_at}`
- 儲存位置跟 locations 一樣放手機 JSON（但獨立檔案 `routes.json`）

## UI 草稿

### 畫路徑模式
```
[地圖]
 ● → ● → ● → ● ←  目前游標位置
           ↑
           waypoint 3 (可拖曳 / 右鍵刪除)

下方控制列：
┌────────────────────────────────────┐
│ Waypoints: 4    距離: 420 m       │
│ [← Back] [↶ Undo] [🗑 Clear] [✓ Done]│
└────────────────────────────────────┘
```

### 播放面板
```
┌─ 路徑播放 ─────────────────────┐
│ 名稱：(未命名路徑)            │
│ 距離：420 m    Waypoints：4   │
│                                │
│ 速度：[===-----]  1.5 m/s     │
│ 間隔：[==------]  1.0 s       │
│                                │
│  [▶ Play] [⏸ Pause] [⏹ Stop]  │
│  [⏭ Skip to next waypoint]    │
│                                │
│ 進度：━━━━━━━━━━━━━━━ 42%      │
│ ETA：約 2 分鐘                │
│                                │
│ [💾 Save as route]             │
└────────────────────────────────┘
```

## 邊界條件
- 瀏覽器 tab 切到背景 → `setInterval` 被節流到 1Hz（能接受，目標 app 每幾秒才讀一次定位）
- 長時間播放 → 提示使用「Wake Lock API」避免螢幕睡著
- 連線斷掉 → 自動暫停，顯示重連提示
- 兩個 waypoint 相距太遠 → 仍支援（速度 1.5 m/s 的話會跑很久），不過 UI 警告「預估 > 1 小時」

## 影響的元件
- **Web**：
  - 地圖畫路徑工具（Leaflet `Polyline` + 自訂 click handler）
  - 路徑狀態機（idle / drawing / playing / paused）
  - 計時器 + 線性插值
  - 地圖路徑渲染
- **Phone**：沿用 `/teleport`，不需改動
  - 可選：新增 `GET/PUT /routes` endpoint（若要存手機）

## 開放問題
- 路徑要不要也存在手機（跟 locations 同等地位）？還是只在 browser session 中用？
  - **MVP 不存**：關 tab 就消失；滿意再儲存為「已命名路徑」
- 插值精度：兩個 waypoint 之間要以多少公尺切？**MVP 用 speed × interval 決定**（例如 1.5 m/s × 1s = 每 1.5 m 一個點）
- 支援迴路播放（走完從頭開始）嗎？nice-to-have

---

## Deferred: GPX Import

延後實作。理由：取得 GPX 檔（從 Strava / Komoot / 自製工具匯出）比在地圖點幾下麻煩許多。優先度低。

當實作時的需求：
- 網頁點「Import GPX」→ 檔案選擇器
- 解析 `<trkpt lat lon>` 序列
- 地圖畫出路徑 + 起終點
- 重用 (2) 播放流程
- 邊界：多段 track（`<trkseg>`）的處理方式（MVP 合併成一條）

技術備註：
- npm 套件：`gpxparser` 或 `xml2js`
- GPX 點通常很密（每秒一個）→ 可能需要 downsample
