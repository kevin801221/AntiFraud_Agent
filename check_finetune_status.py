from openai import OpenAI
import os
from dotenv import load_dotenv
import time

# 載入環境變數
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def check_status(job_id):
    job = client.fine_tuning.jobs.retrieve(job_id)
    print(f"\nJob Status: {job.status}")
    
    if hasattr(job, 'fine_tuned_model') and job.fine_tuned_model:
        print(f"Fine-tuned model ID: {job.fine_tuned_model}")
    
    events = client.fine_tuning.jobs.list_events(
        fine_tuning_job_id=job_id,
        limit=10
    )
    print("\nLatest events:")
    for event in events.data:
        print(f"- {event.message}")

# 你的fine-tuning job ID
job_id = "ftjob-89zNSfQ3y71PVelVjK8Ri3SW"

while True:
    check_status(job_id)
    time.sleep(60)  # 每60秒檢查一次
