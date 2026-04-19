# 07 · Auto Plant

## 狀態
📝 **Spec** — 未實作。

## 目標
玩家在網頁設定一個圓形範圍（中心點 + 300 m 半徑），按下開始後，程式在圓內隨機抽目標點、以 16 km/h 速度向該點移動、抵達後再抽新點，無限循環 — 用來掛機**自動種花**。

## Actor
玩家（純掛機刷花，人不在電腦前）

## 前提條件
- Mock GPS app 背景運行、網頁連得上
- 玩家對圓心位置有選擇（e.g. 家附近、公園）

## 遊戲機制（Pikmin wiki 參考）
- 世界切成 **5 m × 5 m grid cell**
- 一個 cell 種花後 **5 min cooldown**
- 速度上限 **16-20 km/h**（取 16 km/h 留 margin）

## 主要流程
1. 頂部按 `🌸 Auto plant` → 進入 **arming** 模式（游標提示「點地圖設定圓心」）
2. 地圖上點一下 → 設為圓心、畫出 300 m 半徑的圓 overlay
3. 底部浮起 bar：`Center: lat, lng · Radius: 300 m · [▶ Start] [× Cancel]`
4. 按 Start → loop 開始
5. Loop 邏輯：
   - 隨機抽圓內一點為 target（uniform distribution）
   - 每秒從目前位置朝 target 走 4.44 m（16 km/h × 1 s）
   - 抵達 target（距離 ≤ 4.44 m）→ 抽新 target
   - 每步 `POST /teleport` + 更新紅點
6. 底部 bar 變成：`🌸 Running · 42 steps · 187 m · 0:35 · [⏹ Stop]`
7. 按 Stop → loop 結束、bar 消失、圓留在地圖上（視覺變淡）

## 參數（硬編碼 MVP）
| 項 | 值 | 備註 |
|---|---|---|
| 速度 | **16 km/h** (4.44 m/s) | wiki 上限 16-20，取保守值 |
| 送頻率 | **1 POST/s** | 避免 server 壓力、符合遊戲 GPS poll |
| 每步距離 | **4.44 m** | 小於 cell 對角線 7.07 m → 每步進新 cell |
| 圓半徑 | **300 m** | 周長 1885 m，走一圈 6.7 min > 5 min cooldown |

## 安全性檢查
- 300 m 圓內有 **~11,300 個 5×5 cell**
- 5 min 走 1333 m → 純隨機亂走回到同 cell 機率很低（birthday paradox 邊界內）
- 極端情況下偶爾重複一個 cell → 可接受（少一朵花，不影響整體產量）

## 非目標（MVP 不做）
- 半徑可調（硬編 300 m）
- 速度可調（硬編 16 km/h）
- 多個圓 / 矩形 / polygon
- 路徑避開障礙物（建築、河流都穿牆）
- Wake lock API、電量提醒
- 種花計數 / 花名 tracking

## 邊界條件 / 已知限制
- **tab 切到背景**：`setInterval` 被瀏覽器節流到 1 Hz → 剛好還是 1 POST/s，不受影響
- **網路斷線**：`/teleport` 失敗 log 到 console、**不中斷 loop**（下一秒重試）
- **手機 mock 被關**：loop 仍跑、紅點在地圖上動，但遊戲沒反應 → 使用者自行察覺（deferred 項目 5 會修）
- **Auto plant 跑時手動點地圖**：忽略 click（不進 pending 模式，避免誤觸）

## UI 草稿
```
─── Idle ───
┌── Warp · [●Connected] · [http://...] · 🎯 · 🌸 Auto plant · Stop mock ──┐

─── Arming（按下 Auto plant 後）───
頂部提示：「點地圖設定圓心 · [× Cancel]」

─── Configured（圓心已設定）───
地圖顯示 300 m 圓 overlay
┌─ Center: 35.681, 139.69 · Radius: 300 m · [▶ Start] [× Cancel] ─┐

─── Running ───
地圖顯示圓 + 紅點在圓內持續移動
┌─ 🌸 Running · 42 steps · 187 m · 0:35 · [⏹ Stop] ─┐
```

## 影響的元件
- **Web**（全部修改集中在此）：
  - `src/lib/geo.ts`（新）：距離 / 方向 / 圓內隨機點 / 朝目標走一步
  - `src/lib/Map.svelte`：新增 circle prop，用 `L.circle` 渲染
  - `src/App.svelte`：auto plant 狀態機、`setInterval` loop、底部 bar
- **Phone**：**不需改動**（沿用 `/teleport`）

## 日後可能的擴充
- 半徑 slider（100 / 300 / 500 / 1000 m）
- 速度 slider（讓使用者找遊戲接受的最高速度）
- 「目前步數 / 小時 vs 遊戲實際種花數」比率觀察 → 驗證速度選擇
- 多個圓任意切換
