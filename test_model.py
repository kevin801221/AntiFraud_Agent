from openai import OpenAI
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def chat_with_model(prompt, model_id="ft:gpt-3.5-turbo-0125:personal::B6GV9v9U"):
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": "你是一個專業的詐騙防範助手，可以幫助用戶識別各種詐騙手法並提供防範建議。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"發生錯誤: {str(e)}"

# 測試案例
test_cases = [
    "最近收到一封email說我中獎了，要我提供銀行帳號領獎金，這是真的嗎？",
    "有人說他是我遠房親戚，急需借錢，要我轉帳給他，我該怎麼辦？",
    "接到自稱是警察的電話，說我涉及洗錢案件，要我配合調查，這是詐騙嗎？"
]

print("開始測試fine-tuned模型...\n")
for i, test_case in enumerate(test_cases, 1):
    print(f"測試案例 {i}:")
    print(f"問題: {test_case}")
    response = chat_with_model(test_case)
    print(f"回答: {response}\n")
    print("-" * 80 + "\n")
