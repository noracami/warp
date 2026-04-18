# 06 · First-Time Setup

## 目標
朋友 clone repo 後，從零到可用。步驟越少越好，Windows 友善（未來）。

## Actor
- 沒碰過這專案的新使用者
- 有 Android 手機 + 電腦 + 同 Wi-Fi

## 前提條件
- 電腦裝有 git、Python（可選）、JDK 17（build APK 時）
- 手機是 Android，開發者選項可存取

## 主要流程（MVP，macOS）

### Step 1: Clone
```bash
git clone git@github.com:noracami/warp.git
cd warp
```

### Step 2: Build & 裝 Android app
```bash
cd android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
> ⚠️ 這步需要 USB + ADB 一次性授權。之後所有操作都不用 ADB

### Step 3: 手機設定
1. 開 Mock GPS app → 授予定位 & 通知權限
2. 點「Open dev settings」→ 選「模擬位置資訊應用程式」→ 選 Mock GPS
3. 回 Mock GPS 首頁，應顯示 `● Running`
4. 記下 IP（例如 `192.168.1.42`）

### Step 4: 開網頁
**選項 A：clone repo 自建**
```bash
cd web
pnpm install
pnpm dev
# 開瀏覽器 → http://localhost:5173
```

**選項 B：已部署版本（若有）**
```
開瀏覽器 → https://noracami.github.io/warp/
```

### Step 5: 填手機 IP
網頁首次載入 → 提示填手機 IP → 填 `192.168.1.42` → 儲存 → 開始用

## 安裝體驗要達到的門檻
- 從 clone 到能送第一個 teleport：**< 10 分鐘**（不含 gradle 首次下載）
- **沒有任何 ADB 指令**（除了一次性裝 APK）
- 不需要自己寫 config 檔
- 錯誤訊息要明確（IP 錯、網段不對、服務沒跑）

## Windows 支援（Phase 2）
- README 獨立章節
- 指令對照：
  - `./gradlew` → `.\gradlew.bat`
  - `cp` → `Copy-Item`
  - `adb install` 同 macOS
- JDK：Temurin Windows installer
- Platform Tools：Google 下載頁直接下載 zip，解壓加 PATH

## 未來簡化方向
- **Release 版 APK 放 GitHub Releases** → 朋友不用 build，直接下載 apk 裝
- **Web app 部署到 GitHub Pages** → 朋友連 clone 都不用
- **Deep link 設定**：手機 app 產 QR → 網頁掃描自動填 IP

理想終態（Phase 3）：
1. 朋友去 Release 頁下載 APK → 裝
2. 開 app → 授權 → 掃 QR 開網頁
3. 網頁自動配對手機 → 立即能用

## 邊界條件
- 公司 / 咖啡店 Wi-Fi 有 AP isolation → LAN 連不到手機，需提示「換網路或開手機熱點」
- 手機 IP 是 DHCP，隔天可能變 → app 首頁永遠顯示當前 IP，網頁 settings 可更新

## 影響的元件
- `README.md`：主流程改寫
- `android/` / `web/`：build 腳本 / 文件
- 未來：GitHub Actions（自動 build APK + deploy web）

## 開放問題
- 要不要做 Release 流程？MVP 不用，等穩定再說
- `locations.example.yaml` 如何轉進 web？MVP 提供「Import sample locations」按鈕內建三筆
