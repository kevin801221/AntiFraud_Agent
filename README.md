# AntiFraud Agent

This project implements an AI-powered fraud detection system that learns from real-world fraud cases to help prevent future scams. It includes both data collection and model fine-tuning components.

## Data Collection and Training Process

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

## Project Structure

- `core/`: Core components of the system
  - `jina_crawler.py`: Web crawler for collecting fraud case data
  - `content_processor.py`: Processes and structures raw crawled content
  - `training_data_generator.py`: Generates training data for the AI model
  - `utils.py`: Utility functions used across the system
- `convert_to_openai_format.py`: Converts training data to OpenAI's chat format for SFT
- `convert_to_dpo_format.py`: Converts training data to OpenAI's DPO format
- `check_finetune_status.py`: Monitors fine-tuning job status
- `main.py`: Main entry point for running the data pipeline

## Setup

1. Clone the repository:
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

## Usage

1. Run the data pipeline to collect and process fraud cases:
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

## Testing the Model

After fine-tuning is complete, you can test the model using the provided test script:

```bash
python test_model.py
```

Example test cases and their responses:

1. Email Scam Detection:
```
Q: 最近收到一封email說我中獎了，要我提供銀行帳號領獎金，這是真的嗎？
A: 這很可能是詐騙郵件，請勿提供個人資料或銀行帳號。建議您立即刪除該郵件，並可以向相關單位舉報。
   記得不要隨意相信來歷不明的郵件或訊息，以免上當受騙。
```

2. Impersonation Scam Detection:
```
Q: 有人說他是我遠房親戚，急需借錢，要我轉帳給他，我該怎麼辦？
A: 這是一種常見的詐騙手法，詐騙者冒充親戚或朋友向您求助，建議您不要隨意轉帳給對方。
   請盡量與親戚核對對方身份以確認真假，並可以聯繫當地警方或詐騙防護專線進行舉報。
   記得不要隨意透露個人資料或進行轉帳操作。
```

3. Police Impersonation Scam:
```
Q: 接到自稱是警察的電話，說我涉及洗錢案件，要我配合調查，這是詐騙嗎？
A: 這是詐騙。警察不會通過電話要求市民轉錢或提供個人資料。請立即掛電話，不要提供個人資料或轉帳。
   詐騙分子可能冒充警察或其他官方機構，試圖騙取個人和金融信息。若有疑慮，應立即與當地警方聯繫。
```

## Note

This project includes both data collection and model fine-tuning components. The training data and fine-tuned models are not included in this repository for privacy and security reasons.
開始監控fine-tuning job: 

Job Status: succeeded
Fine-tuned model ID: ft:gpt-3.5-turbo-0125:personal::

訓練完成！你可以使用這個模型ID來進行推理了。
