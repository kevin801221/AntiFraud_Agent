from openai import OpenAI
import os
from dotenv import load_dotenv
import time
import sys

# 載入環境變數
load_dotenv()

# 檢查是否提供了job ID
if len(sys.argv) < 2:
    print("請提供fine-tuning job ID作為參數")
    print("使用方式: python check_finetune_status.py <job_id>")
    sys.exit(1)

job_id = sys.argv[1]
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def check_status(job_id):
    try:
        # 獲取job狀態
        job = client.fine_tuning.jobs.retrieve(job_id)
        print(f"\nJob Status: {job.status}")
        
        # 如果已完成，顯示模型ID
        if hasattr(job, 'fine_tuned_model') and job.fine_tuned_model:
            print(f"Fine-tuned model ID: {job.fine_tuned_model}")
            if job.status == "succeeded":
                print("\n訓練完成！你可以使用這個模型ID來進行推理了。")
                return True
        
        # 獲取最新事件
        try:
            events = client.fine_tuning.jobs.list_events(
                fine_tuning_job_id=job_id,
                limit=10
            )
            print("\nLatest events:")
            for event in events.data:
                print(f"- {event.message}")
        except Exception as e:
            print(f"獲取事件時發生錯誤: {str(e)}")
        
        # 如果job失敗，停止檢查
        if job.status == "failed":
            print("\n訓練失敗！請檢查錯誤信息。")
            return True
            
        return False
            
    except Exception as e:
        print(f"檢查狀態時發生錯誤: {str(e)}")
        return False

print(f"開始監控fine-tuning job: {job_id}")
while True:
    try:
        if check_status(job_id):
            break
        print("\n60秒後重新檢查...")
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n監控已停止")
        break
    except Exception as e:
        print(f"發生錯誤: {str(e)}")
        print("5秒後重試...")
        time.sleep(5)
