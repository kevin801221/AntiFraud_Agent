# AntiFraud Agent

這個專案實現了一個由 AI 驅動的反詐騙系統，結合了多種先進技術來分析、理解和預防詐騙案件。系統不僅可以從真實案例中學習，還能分析視頻教育內容，提供全方位的反詐騙解決方案。

## 系統功能

本系統包含四個主要功能模塊：

1. **詐騙案例收集與分析**
   - 使用 JinaCrawler 爬取警政署反詐騙網站的案例
   - 處理和結構化原始數據
   - 生成訓練數據用於模型優化

2. **視頻內容智能分析**
   - 自動下載和處理 YouTube 反詐騙教育視頻
   - 使用 GPT-4V 分析視頻關鍵幀
   - 生成詳細的視頻內容報告
   - 提供互動式網頁儀表板展示分析結果

3. **圖像理解與警示**
   - 分析詐騙相關圖片
   - 識別詐騙手法和警告標誌
   - 提供預防建議

4. **模型訓練與優化**
   - 支持 SFT（監督式微調）
   - 支持 DPO（直接偏好優化）
   - 持續改進模型效果

## 數據處理流程

The training data is collected and processed through the following pipeline:

1. **Web Crawling**: Using the JinaCrawler component, we crawl fraud case information from the Taiwan National Police Agency's Anti-Fraud website. This provides us with real-world fraud cases and prevention information.

2. **Content Processing**: The ContentProcessor component processes the crawled data, cleaning and structuring the raw HTML content into meaningful fraud case information.

3. **Training Data Generation**: The TrainingDataGenerator transforms the processed content into a format suitable for training language models. This includes:
   - Extracting fraud patterns and techniques
   - Identifying scammer behaviors and tactics
   - Capturing victim responses and outcomes
   - Generating appropriate counter-measures and prevention strategies

4. **Model Fine-tuning**: The processed data is used to fine-tune language models for better fraud detection and prevention:
   - Converting data into OpenAI's chat format
   - Supporting both SFT (Supervised Fine-Tuning) and DPO (Direct Preference Optimization)
   - Training models to provide detailed fraud prevention advice

## 專案結構

- `src/`: 源代碼目錄
  - `Youtube_analysis_AntifraudVideo.py`: YouTube 視頻分析工具
  - `youtube_auto_image_understanding.py`: 圖像理解工具
  - `jina_crawler.py`: 網頁爬蟲組件
  - `content_processor.py`: 內容處理組件
  - `training_data_generator.py`: 訓練數據生成器

- `core/`: 核心系統組件
  - `jina_crawler.py`: Web crawler for collecting fraud case data
  - `content_processor.py`: Processes and structures raw crawled content
  - `training_data_generator.py`: Generates training data for the AI model
  - `utils.py`: Utility functions used across the system
- `convert_to_openai_format.py`: Converts training data to OpenAI's chat format for SFT
- `convert_to_dpo_format.py`: Converts training data to OpenAI's DPO format
- `check_finetune_status.py`: Monitors fine-tuning job status
- `main.py`: Main entry point for running the data pipeline

## 安裝設置

1. 克隆代碼庫：
```bash
git clone https://github.com/kevin801221/AntiFraud_Agent.git
cd AntiFraud_Agent
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
- Copy `.env.example` to `.env`
- Fill in your OpenAI API key in `.env`:
  ```
  OPENAI_API_KEY=your_openai_api_key_here
  ```

## 使用說明

1. **案例收集與處理**：
```bash
python main.py
```

2. **視頻分析**：
```bash
# 分析單個視頻
python src/Youtube_analysis_AntifraudVideo.py --urls "VIDEO_URL"

# 批量分析視頻
python src/Youtube_analysis_AntifraudVideo.py --url-file data/video_urls.txt
```

3. **查看分析結果**：
```bash
# 啟動網頁服務
cd output/video_analysis
python -m http.server 8080
```
然後訪問：http://localhost:8080/dashboard.html

4. **運行數據處理管道**：
```bash
python main.py
```

2. Convert training data to OpenAI's format:
```bash
# For Supervised Fine-Tuning (SFT)
python convert_to_openai_format.py

# For Direct Preference Optimization (DPO)
python convert_to_dpo_format.py
```

3. Start model fine-tuning:
```bash
# Monitor fine-tuning progress
python check_finetune_status.py
```

## Model Fine-tuning

This project supports two fine-tuning approaches:

1. **Supervised Fine-Tuning (SFT)**:
   - Uses direct instruction-output pairs
   - Suitable for teaching the model basic fraud detection patterns
   - Recommended for initial model training

2. **Direct Preference Optimization (DPO)**:
   - Uses preferred vs non-preferred response pairs
   - Helps model learn to provide more detailed and helpful responses
   - Can be used after SFT for further optimization

## 注意事項

1. **API 密鑰**：
   - 確保在 `.env` 文件中設置了必要的 API 密鑰
   - 主要包括：OPENAI_API_KEY（用於 GPT-4V 分析）

2. **資源使用**：
   - 視頻分析可能消耗較多 API 額度
   - 建議先用較短的視頻進行測試

3. **數據安全**：
   - 本代碼庫不包含訓練數據和微調後的模型
   - 所有案例數據都應該謹慎處理

4. **系統要求**：
   - Python 3.8 或更高版本
   - 足夠的硬盤空間用於存儲視頻和分析結果
   - 穩定的網絡連接
