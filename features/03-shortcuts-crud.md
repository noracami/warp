# 03 · Shortcuts CRUD

## 目標
玩家收藏常去地點（Home / Office / 特定花圃），清單管理。**清單存在手機**，所有 client 透過 HTTP 存取。並可匯出 JSON 備份。

## Actor
玩家

## 前提條件
- Web SPA 能運作
- 地圖正常顯示
- 手機 app 運行中（提供 `GET/PUT /locations`）

## 主要流程

### 新增快捷地點（從網頁）
1. 在地圖上找到位置（hover / 右鍵 / 點擊）
2. 選單點「Save as shortcut」
3. Modal 填：name（必填）、tags（選）、note（選）
4. 儲存 → `PUT /locations`（整個 list 覆寫）→ 清單更新

### 新增快捷地點（從遊戲，**關鍵情境**）
1. 遊戲內點某個花 → 「在地圖中開啟」
2. Android 自動開 Google Maps（寫死，沒選單）並 pin 該位置
   > ⚠️ 這步是完整 app 切換，**記憶體受限的手機可能會把遊戲 kill 掉**。屬硬體限制，工具無法解決
3. 在 Google Maps 按分享按鈕 → 分享選單出現（overlay，不離開 Google Maps）
4. 選 **Warp** → Warp 接到 `ACTION_SEND` intent
5. Warp 解析分享的 URL/text → 抽出 lat/lng → 加進手機的 JSON
6. Warp 顯示 Toast「✓ 已新增為 `Pin 35.68, 139.69`」並自動返回 Google Maps
7. 使用者決定是否切回遊戲
   - 硬體充足的手機：遊戲背景還在，直接切回繼續玩
   - 硬體受限的手機：遊戲已被 kill，需要重新開啟；此情境下本功能主要用於「事後整理清單」
8. 下次打開網頁，`GET /locations` 就看到了

### 傳送到快捷地點
1. 右側清單點某個 shortcut
2. 一鍵 `POST /teleport` 手機
3. 清單項目短暫高亮確認

### 編輯 / 刪除
1. 清單項 hover 出現 ⋯ menu
2. Edit → 開同樣 modal → `PUT /locations`
3. Delete → 確認 dialog → `PUT /locations`

### 匯出
1. Settings → 「Export JSON」
2. 網頁先 `GET /locations` 拿最新版
3. 產生檔案下載：`warp-locations-<date>.json`

### 匯入
1. Settings → 「Import JSON」→ 選檔
2. 選擇「覆蓋」或「合併」策略
3. `PUT /locations` 寫回手機

## 資料格式

```json
{
  "version": 1,
  "exported_at": "2026-04-19T10:30:00Z",
  "locations": [
    {
      "id": "uuid",
      "name": "Home",
      "lat": 25.033964,
      "lng": 121.564472,
      "tags": ["Taipei", "outdoor"],
      "timezone": "Asia/Taipei",
      "note": "Taipei 101",
      "created_at": "2026-04-19T10:00:00Z"
    }
  ]
}
```

## UI 草稿
```
右側欄位：

📍 Locations (5)           [⋯]
─────────────────────────
🔍 [search...]
─────────────────────────
⭐ Home           Taipei
   Shibuya Cross  Tokyo
   Tokyo Tower    Tokyo
   Osaka Castle   Osaka
   Test Site      Taipei
─────────────────────────
+ Save current
```

## 邊界條件
- 手機存 flat JSON（`files/locations.json`），容量上限幾乎無限（MB 等級）
- 多 client 同時編輯 → 最後 PUT 贏（MVP 不做樂觀鎖；之後若有需要加 `If-Match: <etag>`）
- 匯入時版本不同 → 檢查 `version` 欄位，不相容時警告
- 從 Google Maps 分享的 URL 格式多樣（`maps.app.goo.gl` 短網址需展開）→ 失敗時 fallback 為座標字串

## 影響的元件
- **Phone**：
  - `LocationStore.kt`：讀寫 `files/locations.json`
  - `LocationsHandler.kt`：`GET/PUT /locations` HTTP endpoints
  - `ShareReceiverActivity.kt`：`ACTION_SEND` intent-filter，接收 Google Maps 分享
  - `UrlParser.kt`：從分享的 URL/文字抽 lat/lng（port Python 的 `parse_location`）
- **Web**：
  - `LocationsApi`（fetch wrapper）
  - `ShortcutList` 元件
  - `LocationModal`（新增 / 編輯）
  - `Settings` 頁（匯出 / 匯入）

## 開放問題
- 手機 share intent 時，是否彈出 dialog 讓使用者取名 + 加 tags？還是直接加為「Pin <時間>」、之後到網頁補？**MVP 直接加為 Pin，Toast 提示**
- 是否按 tag 分群 / 過濾？MVP 只做搜尋
- 是否保留現有 `locations.example.yaml` 作為 onboarding 示例？可以在首次開啟時讓使用者匯入
- 是否加「最近去過」自動清單？nice-to-have
- PUT 失敗（手機離線）時，網頁怎麼處理？MVP：跳錯誤訊息，操作保留在網頁暫存，使用者可重試
