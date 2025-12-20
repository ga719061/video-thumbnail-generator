# 🎬 影片縮圖產生器 (Video Thumbnail Generator)

批次為影片生成縮圖，支援 Synology Video Station 格式。

## ✨ 功能特色

- **批次處理** - 選擇多個資料夾，自動遞迴掃描所有影片
- **自訂截取時間** - 可指定秒數或留空使用影片中間幀
- **雙輸出模式**
  - **與影片同目錄**：生成 `影片名.jpg`
  - **Synology Video Station (SSH)**：自動寫入 `@eaDir/影片檔名/SYNOVIDEO_VIDEO_SCREENSHOT.jpg`
- **🔄 覆蓋模式** - 支援重新生成並覆蓋現有的縮圖
- **📈 處理記錄** - 自動儲存處理歷史，避免重複掃描（即使刪除縮圖也會自動偵測並補回）
- **🧹 清除工具** - 一鍵清理選取資料夾中的所有縮圖（支援 SSH 遠端清理）
- **💾 自動儲存** - 啟動時自動載入上次的 SSH 設定與資料夾清單（密碼除外）
- **SSH/SFTP 直接寫入** - 無需掛載網路硬碟，直接透過 SSH 協定管理 NAS 縮圖
- **完整控制** - 支援暫停、繼續、停止處理

## 📦 支援格式

`.mp4` `.avi` `.mkv` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpeg` `.mpg` `.3gp`

## 🖥️ 使用方式

### 基本使用（本機模式）

1. 選擇「與影片同目錄（同名.jpg）」模式
2. 點擊「新增資料夾」選擇影片資料夾
3. 設定截取時間（秒）或留空
4. 點擊「開始處理」

### Synology Video Station 模式

1. 選擇「Synology Video Station（SSH）」模式
2. 填寫 NAS SSH 連線資訊：
   - **NAS IP**: NAS 的 IP 位址
   - **端口**: SSH 端口（預設 22）
   - **帳號/密碼**: SSH 登入資訊
3. 設定路徑對應：
   - **磁碟機**: Windows 網路磁碟代號（如 `Y`）
   - **共享資料夾**: NAS 共用資料夾名稱（如 `video`）
4. 點擊「測試連線」查看共享資料夾清單
5. 新增資料夾並開始處理

### 🧹 清除功能使用

如果想重新開始或清理舊縮圖，可點擊「清除縮圖」按鈕。
- **本機模式**：會刪除所有影片對應的 `.jpg` 檔案。
- **SSH 模式**：會刪除 `@eaDir` 內部的縮圖子資料夾。
- 清除後會自動同步處理歷史記錄。

## ⚙️ NAS 設定要求

1. **啟用 SSH**  
   DSM → 控制台 → 終端機 → 勾選「啟用 SSH 服務」

2. **檔案權限**  
   建議使用具有目標夾管理權限的帳號。

## 📝 縮圖規格

- **解析度**: 寬度固定為 800px（等比縮放）
- **格式**: JPEG (品質 90%)
- **檔名**: `SYNOVIDEO_VIDEO_SCREENSHOT.jpg` (Video Station 專用)

## 🔧 開發資訊

### 依賴套件

```bash
pip install opencv-python paramiko pyinstaller
```

### 打包 EXE

```bash
pyinstaller --clean VideoThumbnailGenerator.spec
```

## 📄 授權

MIT License
