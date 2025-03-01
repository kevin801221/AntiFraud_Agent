import json
import jsonlines

def create_non_preferred_output(output):
    """
    創建一個較差的回答版本作為non-preferred output
    這個版本會：
    1. 移除具體的建議和細節
    2. 使用較為模糊的表述
    3. 省略重要的防範步驟
    """
    # 基本的簡短回答模板
    if "辨識" in output:
        return "這種詐騙很常見，要小心提防就好了。記得不要輕易相信網路上的廣告。"
    elif "處理" in output:
        return "可以向警察報案，或是找相關單位協助。"
    elif "警示" in output:
        return "主要就是要看對方的行為是否可疑，如果感覺不對就要提高警覺。"
    else:
        return "需要注意這類詐騙，保持警覺即可。"

def convert_to_dpo_format(input_file, output_file):
    # 讀取輸入的JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 轉換為OpenAI的DPO格式
    dpo_format = []
    for example in data['sft_data']:
        dpo_example = {
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一個專業的詐騙防範助手，可以幫助用戶識別各種詐騙手法並提供防範建議。"
                    },
                    {
                        "role": "user",
                        "content": example['instruction']
                    }
                ],
                "tools": [],
                "parallel_tool_calls": True
            },
            "preferred_output": [
                {
                    "role": "assistant",
                    "content": example['output']
                }
            ],
            "non_preferred_output": [
                {
                    "role": "assistant",
                    "content": create_non_preferred_output(example['output'])
                }
            ]
        }
        dpo_format.append(dpo_example)
    
    # 寫入JSONL文件
    with jsonlines.open(output_file, mode='w') as writer:
        for example in dpo_format:
            writer.write(example)

if __name__ == "__main__":
    input_file = "fraud_data/03_training_data/training_data_20250301_172955.json"
    output_file = "fraud_data/03_training_data/dpo_training_data_openai.jsonl"
    convert_to_dpo_format(input_file, output_file)
    print(f"Conversion completed. Output saved to {output_file}")
