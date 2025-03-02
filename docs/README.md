# YouTube 影片分析系統

這是一個強大的 YouTube 影片分析工具，可以自動下載影片、擷取關鍵幀，並使用 GPT-4V 進行智能分析。系統會生成詳細的分析報告，並提供美觀的網頁介面來展示結果。

## 功能特點

- 自動下載 YouTube 影片
- 每隔固定時間擷取影片幀
- 使用 GPT-4o 分析每個幀的內容
- 生成整體影片摘要
- 提供互動式網頁儀表板
- 支援批次處理多個影片
- 自動生成 HTML 報告

## 環境設置

1. 首先確保您已安裝 Python 3.8 或更高版本

2. 安裝所需的依賴：
```bash
pip install yt-dlp openai opencv-python tqdm langsmith python-dotenv
```

3. 設置環境變數：
   創建 `.env` 文件並添加以下內容：
```env
OPENAI_API_KEY=your_openai_api_key
LANGSMITH_API_KEY=your_langsmith_api_key  # 可選
LANGSMITH_PROJECT=video_analysis          # 可選
```

## 添加要分析的影片

有兩種方式可以添加要分析的影片：

1. **直接在命令行指定 URL**：
```bash
python Youtube_analysis_AntifraudVideo.py --urls "https://www.youtube.com/watch?v=VIDEO_ID1" "https://www.youtube.com/watch?v=VIDEO_ID2"
```

2. **使用文本文件批次處理**：
   1. 創建一個文本文件（例如 `video_urls.txt`）
   2. 每行添加一個 YouTube 影片 URL
   3. 執行命令：
```bash
python Youtube_analysis_AntifraudVideo.py --url-file video_urls.txt
```

## 命令行選項

- `--urls`: 直接指定 YouTube URL（可多個）
- `--url-file`: 指定包含 URL 的文本文件
- `--output`: 指定輸出目錄（預設：video_analysis）
- `--interval`: 擷取幀的時間間隔（秒）（預設：10）
- `--max-duration`: 最大處理時長（秒）（0 表示處理整個影片）
- `--max-workers`: 最大並行處理數（預設：3）
- `--force`: 強制重新處理已分析過的影片
- `--skip-analysis`: 只下載和擷取幀，不進行分析

## 查看分析結果

1. **啟動網頁服務**：
```bash
cd video_analysis  # 進入輸出目錄
python -m http.server 8080  # 啟動本地服務器
```

2. **訪問儀表板**：
   - 打開瀏覽器訪問：http://localhost:8080/dashboard.html
   - 儀表板提供：
     - 影片分析統計
     - 每個影片的詳細分析
     - 時間軸上的幀分析
     - 整體影片摘要

## 輸出目錄結構

```
video_analysis/
├── dashboard.html              # 主儀表板
├── master_report.html         # 總體報告
└── YYYYMMDD_HHMMSS_VideoTitle_hash/  # 每個影片的目錄
    ├── frames/                # 擷取的幀
    ├── video_info.json       # 影片信息
    ├── frame_analyses.json   # 幀分析結果
    ├── video_summary.txt     # 影片摘要
    └── report.html           # 單個影片的報告
```

## 注意事項

1. 確保您有足夠的 OpenAI API 額度
2. 影片分析可能需要一些時間，特別是對於較長的影片
3. 建議先用較短的影片測試系統
4. 如果遇到錯誤，檢查：
   - API 密鑰是否正確設置
   - 網絡連接是否正常
   - 影片 URL 是否有效

## 性能優化

- 使用 `--interval` 調整幀擷取頻率
- 使用 `--max-duration` 限制處理時長
- 調整 `--max-workers` 以優化並行處理

## 故障排除

1. 如果網頁無法訪問：
   - 確認服務器是否正在運行
   - 檢查端口是否被占用
   - 嘗試使用不同的端口

2. 如果影片下載失敗：
   - 確認 URL 是否有效
   - 檢查網絡連接
   - 確認 yt-dlp 是否最新版本

3. 如果分析失敗：
   - 檢查 API 密鑰
   - 查看錯誤信息
   - 使用 `--force` 重試

## 更新日誌

- 2025-03-02: 
  - 新增網頁儀表板
  - 改進錯誤處理
  - 優化並行處理
  - 添加更多命令行選項
