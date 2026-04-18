# 05 · Phone App Home

## 目標
Mock GPS app 首頁作為系統狀態面板：顯示 IP（給使用者填入網頁 / CLI）、運行狀態、當前位置、最近 teleport 時間、**locations 清單筆數**。

## Actor
玩家（只會短暫打開確認狀態，平時在背景）

## 前提條件
- App 已裝、`ACCESS_MOCK_LOCATION` 已允許
- 開發者選項已選 Mock GPS 為模擬位置 app

## 主要流程
1. 開啟 app
2. 首頁顯示當前狀態資訊
3. 複製 IP（或掃 QR code）
4. 關掉 app 去玩遊戲

## UI 草稿
```
┌─ Mock GPS ────────────────────────┐
│                                   │
│        ● Running                  │
│                                   │
│   Listening at                    │
│   ┌─────────────────────────┐     │
│   │ http://192.168.1.42:8080│     │
│   │   [📋 Copy]  [📷 QR]    │     │
│   └─────────────────────────┘     │
│                                   │
│   Current location                │
│   25.033964, 121.564472           │
│                                   │
│   Last teleport                   │
│   5 seconds ago                   │
│                                   │
│   Saved locations                 │
│   12 places · last added 3h ago   │
│                                   │
│   [Open dev settings]             │
│   [Stop mock]                     │
└───────────────────────────────────┘
```

## 顯示欄位

| 欄位 | 來源 | 更新頻率 |
|---|---|---|
| Status (● Running / ○ Stopped) | Service state | 即時 |
| IP | `WifiManager.connectionInfo.ipAddress` | Activity resume 時 |
| Port | 固定 `8080`（可改） | 靜態 |
| QR code | 上面 IP URL 產生 | IP 變時 |
| Current location | `MockLocationService.currentLocation` | 每 1s |
| Last teleport | 計算 `now - lastTeleportAt` | 每 1s |
| Saved locations count | `LocationStore.count()` | 清單有變時 |

## 邊界條件
- Wi-Fi 未連接 → IP 區塊顯示「Not connected to Wi-Fi」+ 重試按鈕
- IP 為 `0.0.0.0` → 同上
- Port 被佔用 → 嘗試 `8080`、`8081`、`8082`，失敗顯示錯誤
- 手機切換網路 → IP 自動更新（監聽 `ConnectivityManager`）

## 影響的元件
- `MainActivity.kt`：改寫 layout，加 IP 顯示、QR、current location、last teleport
- `MockLocationService.kt`：暴露 `lastTeleportAt: Long` 給 Activity
- 新增 `HttpServerService.kt`（或整合進 `MockLocationService`）：NanoHTTPD，管 IP 顯示
- QR code 產生：`com.google.zxing:core`

## 開放問題
- QR code 要內嵌什麼？
  - 純 URL `http://192.168.1.42:8080` → 手機掃後開瀏覽器（怪）
  - 自訂 schema `warp://192.168.1.42:8080` → 讓網頁 app 之後能深度連結
  - JSON 含 IP + port → 網頁 QR scanner 掃一下自動填
  - **MVP 用純 URL**，網頁掃描靠 JS QR scanner
- 手機 app 要不要 **最近 teleport log**（最近 10 筆）？nice-to-have，debug 時有用
