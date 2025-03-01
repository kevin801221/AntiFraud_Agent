from openai import OpenAI
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 上傳文件
with open("fraud_data/03_training_data/formatted_training_data_openai.jsonl", "rb") as file:
    response = client.files.create(
        file=file,
        purpose="fine-tune"
    )
file_id = response.id
print(f"File uploaded with ID: {file_id}")

# 創建DPO fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file_id,
    model="gpt-3.5-turbo-0125",
    method={
        "type": "supervised",
        "supervised": {
            "hyperparameters": {
                "n_epochs": 3,
                "learning_rate_multiplier": 0.1
            }
        }
    }
)

print(f"Fine-tuning job created: {job.id}")

# 監控job狀態
job_status = client.fine_tuning.jobs.retrieve(job.id)
print(f"Job status: {job_status.status}")

# 列出job的事件
events = client.fine_tuning.jobs.list_events(
    fine_tuning_job_id=job.id,
    limit=10
)
for event in events.data:
    print(f"Event: {event.message}")
