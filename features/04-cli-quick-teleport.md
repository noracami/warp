# 04 · CLI Quick Teleport

## 目標
不想開瀏覽器時，terminal 一行搞定 teleport。為老使用者保留輕量入口。

## Actor
- 開發者 / 重度使用者（能開 terminal）
- 在遠端 session / SSH 中

## 前提條件
- Python 3.12+ 已裝
- `uv sync` 完成
- 知道手機 IP（首次設定存 `~/.config/warp/config.toml` 或環境變數）

## 主要流程

### 設定 IP
```bash
gps config --phone-ip 192.168.1.42
# or
export WARP_PHONE_IP=192.168.1.42
```

### 單次 teleport
```bash
gps teleport "25.03,121.56"
gps teleport "https://maps.app.goo.gl/xxxx"   # Google Maps 短網址
gps teleport "https://www.google.com/maps/@35.68,139.69,15z"
```

### 停止
```bash
gps stop
```

### TUI（降級版）
```bash
gps dashboard
```

### TUI 草稿
```
┌──── Warp TUI · 192.168.1.42 ────────┐
│                                     │
│ Paste coords or URL:                │
│ > 25.033964, 121.564472             │
│ [Enter] to send                     │
│                                     │
│ Recent (session-only):              │
│   25.03, 121.56    (2 min ago)      │
│   35.68, 139.69    (10 min ago)     │
│                                     │
│ s = stop    q = quit                │
└─────────────────────────────────────┘
```

## 從現狀的簡化
目前 `main.py` / `tui.py` 的：
- ✅ 保留：`parse_location`（URL 解析）、`teleport` 指令、`stop` 指令、TUI 貼座標
- ❌ 拿掉：`locations.yaml` 相關（`list`、`add`、`--from Name` 查找）
- ❌ 拿掉：`move` 指令（改由 web 負責）
- ❌ 拿掉：TUI 方向鍵走路、清單 CRUD 畫面
- ❌ 拿掉：ADB transport

## 邊界條件
- 手機 IP 未設定 → 清楚錯誤訊息提示 `gps config`
- 連線超時 → 3 秒 timeout，建議檢查手機是否在同網段
- URL 解析失敗 → 回退到原始字串錯誤訊息

## 影響的元件
- Python：`main.py` 大幅簡化（可能從 ~500 行降到 ~150 行）
- `tui.py` 簡化成單一 paste + history 畫面
- `pyproject.toml`：可能移除 `pyyaml`（不再需要）

## 開放問題
- TUI 的「Recent history」是否持久化？MVP 僅 session-only
- 要不要保留 `locations.example.yaml` 的 import 指令，讓舊 user 一鍵轉進 web localStorage？（透過產生 JSON 給網頁匯入）
