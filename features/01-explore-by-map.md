# 01 · Explore by Map

## 目標
玩家坐電腦前玩目標遊戲，用網頁地圖即時點擊 teleport，探索附近的花。這是**主要使用情境**。

## Actor
玩家（電腦 + 手機同時在手邊）

## 前提條件
- Mock GPS app 已在手機背景運行
- 電腦開 warp 網頁，已填入手機 IP，連線正常
- 手機前景是目標遊戲

## 主要流程
1. 玩家看 warp 地圖（目前位置大頭針居中）
2. 在地圖別處點一下
3. 網頁 `POST /teleport` → 手機 `LocationManager.setTestProviderLocation`
4. 玩家視線切到遊戲，看附近是否有花
5. 沒花 → 再點別處；有花 → 可選擇存成快捷地點

## UI 草稿
```
┌──────────────────────────────────────┐
│ Warp · 📡 192.168.1.42  ● Connected │
├────────────────────┬─────────────────┤
│                    │ 📍 Locations    │
│                    │ ─────────────── │
│   [地圖，中間大    │ ⭐ Home         │
│    頭針 = 目前位   │    Shibuya      │
│    置]             │    Tokyo Tower  │
│                    │ ─────────────── │
│                    │ + Save current  │
└────────────────────┴─────────────────┘
```

## 邊界條件
- 手機離線 / IP 改變 → 顯示連線錯誤，提示使用者去手機 app 看新 IP
- 使用者連點過快 → client side debounce（~150ms）或直接丟最新一個
- 點在海上 / 不合理座標 → 允許（使用者自負，不做過濾）

## 影響的元件
- Web：地圖（Leaflet + OSM tiles）、HTTP client、「目前位置」state
- Phone：`POST /teleport {lat, lng}` endpoint

## 非目標（MVP 不做）
- **鍵盤 shortcut**：全部操作以滑鼠 / 觸控為主，不綁快捷鍵
- 地圖上 hover 顯示詳細資訊、地圖圖層切換（衛星 / 街景）等

## 開放問題
- **地圖大頭針要反映手機「實際」位置嗎？**
  - (a) Web 自己記得剛剛送的座標（optimistic）
  - (b) 手機提供 `GET /status` 回傳 `current_location`（source of truth）
  - **MVP 用 (a)**，未來考慮 (b)
- 是否顯示「最近 N 個 teleport 歷史」的 trail 線？可選功能
