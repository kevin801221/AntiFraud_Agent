import openai
import time
from dotenv import load_dotenv
import os
load_dotenv()
# 你的 API 金鑰
openai.api_key = os.getenv('OPENAI_API_KEY')

# 步驟 1: 上傳你的 JSONL 檔案到 OpenAI
def upload_file(file_path):
    response = openai.File.create(
        file=open(file_path),
        purpose='fine-tune'
    )
    print("File uploaded successfully:", response['id'])
    return response['id']

# 步驟 2: 開始微調
def fine_tune_model(file_id):
    response = openai.FineTune.create(
        training_file=file_id,
        model="curie",  # 可以根據需要選擇不同的模型，例如: "davinci", "curie", "babbage", 等等
        n_epochs=4  # 設定訓練的 epoch 數量
    )
    print("Fine-tuning started:", response['id'])
    return response['id']

# 步驟 3: 監控微調進程
def monitor_fine_tune(fine_tune_id):
    while True:
        response = openai.FineTune.retrieve(id=fine_tune_id)
        status = response['status']
        print(f"Fine-tuning status: {status}")

        if status in ['succeeded', 'failed']:
            print(f"Fine-tuning {status}")
            break
        
        time.sleep(60)  # 每分鐘檢查一次進度

# 使用範例
file_path = '/Users/kevinluo/application/Fraud_rebuild/fraud_data/03_training_data/formatted_training_data_openai.jsonl'  # 你上傳的 JSONL 檔案
file_id = upload_file(file_path)  # 上傳檔案
fine_tune_id = fine_tune_model(file_id)  # 開始微調
monitor_fine_tune(fine_tune_id)  # 監控微調進程