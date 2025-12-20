# 🎬 影片縮圖產生器 (Video Thumbnail Generator)

批次為影片生成縮圖，支援 Synology Video Station 格式。

## ✨ 功能特色

- **批次處理** - 選擇多個資料夾，自動遞迴掃描所有影片
- **可調截取時間** - 自訂縮圖截取的秒數（預設 10 秒）
- **雙輸出模式**
  - 與影片同目錄（`影片名.jpg`）
  - Synology Video Station（`@eaDir/影片檔名/SYNOVIDEO_VIDEO_SCREENSHOT.jpg`）
- **SSH/SFTP 支援** - 可直接寫入 NAS 的 `@eaDir` 資料夾
- **智慧跳過** - 已有縮圖的影片自動跳過
- **暫停/繼續/停止** - 完整的處理控制
- **即時日誌** - 顯示處理進度和結果

## 📦 支援格式

`.mp4` `.avi` `.mkv` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpeg` `.mpg` `.3gp`

## 🖥️ 使用方式

### 基本使用（本機同目錄）

1. 選擇「與影片同目錄（同名.jpg）」模式
2. 點擊「新增資料夾」選擇影片資料夾
3. 設定截取時間（秒）
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
4. 點擊「測試連線」確認設定正確
5. 新增資料夾並開始處理

## ⚙️ NAS 設定要求

1. **啟用 SSH**  
   DSM → 控制台 → 終端機 → 勾選「啟用 SSH 服務」

2. **確認共享資料夾名稱**  
   使用「測試連線」按鈕查看可用的共享資料夾

## 📝 縮圖規格

- **解析度**: 800px 寬（等比縮放）
- **格式**: JPEG（品質 90%）
- **截取位置**: 指定秒數，若影片較短則取中間幀

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
