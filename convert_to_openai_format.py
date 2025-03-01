import json
import jsonlines

def convert_to_openai_format(input_file, output_file):
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert each example to OpenAI's chat format
    openai_format = []
    for example in data['sft_data']:
        chat_example = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一個專業的詐騙防範助手，可以幫助用戶識別各種詐騙手法並提供防範建議。"
                },
                {
                    "role": "user",
                    "content": example['instruction']
                },
                {
                    "role": "assistant",
                    "content": example['output']
                }
            ]
        }
        openai_format.append(chat_example)
    
    # Write to JSONL file
    with jsonlines.open(output_file, mode='w') as writer:
        for example in openai_format:
            writer.write(example)

if __name__ == "__main__":
    input_file = "fraud_data/03_training_data/training_data_20250301_172955.json"
    output_file = "fraud_data/03_training_data/formatted_training_data_openai.jsonl"
    convert_to_openai_format(input_file, output_file)
    print(f"Conversion completed. Output saved to {output_file}")
