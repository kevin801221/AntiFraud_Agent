import json

def convert_sft_to_openai_jsonl(sft_file_path, output_file_path):
    # 讀取原始的 SFT JSON 數據
    with open(sft_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取 sft_data
    sft_data = data["sft_data"]
    
    # 轉換為 OpenAI 微調格式
    openai_data = []
    for entry in sft_data:
        prompt = entry['instruction']
        completion = entry['output']
        
        openai_entry = {
            "prompt": prompt + "\n",  # 可以選擇性地在 prompt 後加上換行符號
            "completion": completion + "\n"  # 在 completion 後加上換行符號
        }
        
        openai_data.append(openai_entry)
    
    # 寫入轉換後的 JSONL 文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for entry in openai_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"轉換成功！轉換後的數據已保存至 {output_file_path}")

# 使用範例
sft_file_path = '/Users/kevinluo/application/Fraud_rebuild/fraud_data/03_training_data/training_data_20250301_172955.json'  # 你的 SFT 檔案路徑
output_file_path = '/Users/kevinluo/application/Fraud_rebuild/fraud_data/03_training_data/formatted_training_data_openai.jsonl'  # 輸出 JSONL 檔案路徑

convert_sft_to_openai_jsonl(sft_file_path, output_file_path)