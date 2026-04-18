# Mock GPS

遠端控制 Android 手機的 GPS 定位。目前正在從 ADB broadcast 架構遷移到 LAN HTTP 架構（見 [`features/`](features/)）。

> ⚠️ **Migration in progress**：Android app 已改為 HTTP server（port 8080）。Python CLI / TUI 目前**暫時無法使用**，待 Phase 1b 完成才會接上 HTTP。下方 CLI / TUI 使用說明是舊版內容，僅供歷史參考。

- **Android 端 Mock GPS app**（`android/`）——HTTP server，接收 `POST /teleport` / `POST /stop`，透過 Android `LocationManager` test provider 模擬位置
- **Python CLI / TUI**（`main.py`、`tui.py`）——舊版走 ADB broadcast，待重寫成 HTTP client

## 功能

- CLI 單次傳送：`gps teleport "25.03,121.56"` 或貼 Google Maps URL
- 命名位置：`locations.yaml` 管理 name / lat / lng / tags / timezone / note
- 移動模擬：連續 teleport 模擬走路軌跡
- **互動儀表板（TUI）**：方向鍵走位、搜尋、貼上、新增，不離開終端機即可操作
- 自動檢查 ADB 連線、多裝置可用 `--serial` 指定

## 系統需求

### Python 端
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Android Platform Tools（`adb` 已加入 PATH）

### Android 端（build 自家 app）
- JDK 17（推薦 Temurin）
- Android SDK（platforms;android-35、build-tools;35.0.0）
- Gradle 8.10+（透過 `gradlew` 自動下載）

## 安裝

### 1. Python 端

```bash
uv sync
```

`uv` 會建立 `.venv/` 並安裝所有依賴。

### 2. 複製位置範本

```bash
cp locations.example.yaml locations.yaml
```

`locations.yaml` 已被 gitignore，可安全放入真實座標。

### 3. Build Android app

```bash
cd android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### 4. 手機端設定

1. 開啟 Mock GPS app，授予定位與通知權限
2. 在 app 內按「開啟開發者選項」→ 選擇「模擬位置資訊應用程式」→ 選 Mock GPS
3. 回到 Mock GPS app，確認顯示 `○ Stopped`

## 使用

### 儀表板（推薦）

```bash
uv run gps dashboard
```

**快捷鍵**

| 按鍵 | 功能 |
|------|------|
| ↑ ↓ ← → | 往 N/S/W/E 走一步 |
| `j` / `k` | 位置清單上下選取 |
| `Enter` | 傳送到選取位置 |
| `+` / `-` | 調整步長（1–100 m） |
| `p` | 貼上座標或 Google Maps URL |
| `/` | 搜尋位置（name / tags / tz / note） |
| `c` | 清除搜尋過濾 |
| `a` | 新增位置（帶入目前座標，可貼 URL 自動填入） |
| `s` | **Exit mock**：停止推送、回真實 GPS |
| `r` | 重新讀取 `locations.yaml` |
| `h` / `F1` | 使用說明 |
| `q` | 離開 |

### CLI

```bash
# 列出裝置
uv run gps devices

# 列出位置（含 tag 過濾）
uv run gps list
uv run gps list --tag Taipei

# 傳送（多種輸入格式皆可）
uv run gps teleport Home
uv run gps teleport "25.03, 121.56"
uv run gps teleport "https://www.google.com/maps/@35.68,139.69,15z"
uv run gps teleport "https://maps.app.goo.gl/xxxx"
uv run gps teleport --lat 25.03 --lng 121.56

# 新增位置
uv run gps add Shibuya --lat 35.6595 --lng 139.7005 \
  --tags Tokyo,crossing --tz Asia/Tokyo --note "Hachiko statue"

# 移動模擬
uv run gps move --from Home --to Office
uv run gps move --from Home --to Office --speed 2.5 --interval 1.0

# 停止 mock（回真實 GPS）
uv run gps stop

# 多裝置時指定 serial
uv run gps teleport Home --serial ABCDEF123
```

## `locations.yaml` 格式

```yaml
locations:
  Home:
    lat: 25.033964
    lng: 121.564472
    tags: [Taipei, outdoor]
    timezone: Asia/Taipei
    note: Taipei 101
```

欄位說明：
- `lat` / `lng`（必填）
- `tags`（選填）— 清單，可用於搜尋過濾
- `timezone`（選填）— IANA 時區名
- `note`（選填）— 備註

## 常見問題

### `找不到 adb 指令`
```bash
brew install --cask android-platform-tools   # macOS
```

### `尚未連接任何已授權的 ADB 裝置`
- USB 線接好，手機彈出「允許 USB 偵錯」按允許
- 或 Wi-Fi：`adb connect <手機 IP>:5555`

### `POST /teleport` 回 200 但位置沒變
- Mock GPS app 要在開發者選項「選擇模擬位置資訊應用程式」被選中
- app 通知列應顯示「Mock GPS · Running」
- 確認 app 首頁顯示的 IP / port 跟你打的 URL 一致（換 Wi-Fi 後 IP 會變）

### Google Maps 位置反覆跳動
Google Play Services 的 Fused Location Provider 混入 Wi-Fi/藍牙掃描結果。
關閉：設定 → 位置 → 位置服務 → Wi-Fi 掃描 / 藍牙掃描。

### 移動模擬想中斷
終端機 `Ctrl+C`。

## 架構

```
warp/
├── main.py              CLI 指令（Typer）
├── tui.py               儀表板（Textual）
├── locations.example.yaml   位置範本
├── locations.yaml       你的真實位置（gitignored）
├── pyproject.toml       uv 專案檔
└── android/             Mock GPS app 原始碼
    ├── app/src/main/
    │   ├── AndroidManifest.xml
    │   ├── java/dev/warp/mockgps/
    │   │   ├── MainActivity.kt
    │   │   ├── MockLocationService.kt   持續推送 mock location
    │   │   └── HttpServer.kt            LAN HTTP server (NanoHTTPD)
    │   └── res/
    └── build.gradle.kts
```

**HTTP 協定**

Android app 啟動即在 port 8080 開 HTTP server。

| Method | Path | Body | 說明 |
|---|---|---|---|
| `POST` | `/teleport` | `{"lat": <float>, "lng": <float>}` | 設定模擬位置，每 500 ms 推到 `gps` 與 `network` test providers |
| `POST` | `/stop` | - | 停止推送（服務保持存活） |
| `GET`  | `/status` | - | `{"running": bool, "lat": float?, "lng": float?, "lastTeleportAt": long?}` |

所有 response 含 CORS headers，允許 browser 直接從網頁打。

## 免責聲明

本工具供開發測試、地圖應用除錯等合法用途。使用者需自行確保使用方式不違反相關應用的服務條款。
