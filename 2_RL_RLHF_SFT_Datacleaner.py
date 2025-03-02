import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple

# 定義輸出目錄
OUTPUT_DIR = "fraud_data/training_ready"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_fraud_types(data: Dict) -> List[Dict]:
    """從結構化數據中提取詐騙類型並構建詳細信息"""
    
    fraud_types = []
    
    # 從OpenAI處理過的數據中獲取詐騙類型
    if "openai_processing" in data and data["openai_processing"]["success"]:
        structured_data = data["openai_processing"]["structured_data"]
        
        # 提取主要詐騙類型
        if "詐騙類型" in structured_data and isinstance(structured_data["詐騙類型"], list):
            for fraud_type in structured_data["詐騙類型"]:
                fraud_info = {
                    "type": fraud_type,
                    "description": "",
                    "prevention": "",
                    "alert_keywords": [],
                    "examples": []
                }
                
                # 嘗試填充更多信息
                if "主要的詐騙警示訊息" in structured_data:
                    fraud_info["description"] = structured_data["主要的詐騙警示訊息"]
                
                if "預防詐騙的建議" in structured_data:
                    fraud_info["prevention"] = structured_data["預防詐騙的建議"]
                
                # 提取關鍵詞（基於詐騙類型的關鍵字）
                keywords = []
                type_words = re.findall(r'\w+', fraud_type)
                keywords.extend(type_words)
                
                # 從描述中提取更多關鍵詞
                if fraud_info["description"]:
                    desc_keywords = extract_keywords(fraud_info["description"])
                    keywords.extend(desc_keywords)
                
                # 過濾並去重關鍵詞
                fraud_info["alert_keywords"] = list(set([k for k in keywords if len(k) > 1]))
                
                # 添加一個簡單示例（後續可以由專家補充）
                fraud_info["examples"].append({
                    "scenario": f"{fraud_type}的典型情況",
                    "context": f"詐騙者利用{fraud_type}手法進行詐騙",
                    "fraudster_message": f"這是一個{fraud_type}的示例詐騙信息",
                    "correct_response": "這是詐騙，我應該拒絕並舉報"
                })
                
                fraud_types.append(fraud_info)
    
    return fraud_types

def extract_keywords(text: str) -> List[str]:
    """從文本中提取關鍵詞"""
    # 常見詐騙相關詞彙
    fraud_related_words = [
        "詐騙", "假冒", "投資", "博弈", "帳戶", "個資", "資料", "冒用", 
        "假的", "騙局", "高報酬", "高獲利", "中獎", "退款", "退稅",
        "綁架", "勒索", "贖金", "緊急", "解除", "警示", "銀行", "轉帳"
    ]
    
    # 提取詞彙
    words = re.findall(r'\w+', text)
    
    # 過濾出與詐騙相關的詞彙
    keywords = [word for word in words if word in fraud_related_words or len(word) >= 3]
    
    return keywords

def generate_qa_pairs(fraud_info: Dict) -> List[Dict]:
    """生成問答對"""
    qa_pairs = []
    
    # 生成問題1：關於詐騙類型的辨識
    qa1 = {
        "question": f"如何辨識{fraud_info['type']}詐騙？",
        "correct_answer": f"辨識{fraud_info['type']}詐騙的方法：{fraud_info['description']}\n\n預防方法：{fraud_info['prevention']}",
        "incorrect_answers": [
            f"{fraud_info['type']}不是常見詐騙手法，不需要特別注意。",
            f"只要對方提供身分證件照片，就能確定不是{fraud_info['type']}詐騙。",
            f"不用擔心，銀行會自動偵測並阻擋{fraud_info['type']}詐騙。"
        ]
    }
    qa_pairs.append(qa1)
    
    # 生成問題2：關於預防方法
    qa2 = {
        "question": f"遇到疑似{fraud_info['type']}，應該如何處理？",
        "correct_answer": f"應立即停止交流，不要提供個人資料或轉帳。可以撥打165反詐騙專線尋求協助，或向警方舉報。{fraud_info['prevention']}",
        "incorrect_answers": [
            f"可以先少量轉帳測試對方是否可靠。",
            f"告訴對方你要查證，觀察他們的反應就能判斷真偽。",
            f"向朋友借錢應急，之後再處理這個問題。"
        ]
    }
    qa_pairs.append(qa2)
    
    # 生成問題3：關於警示跡象
    keywords = ", ".join(fraud_info["alert_keywords"][:5]) if fraud_info["alert_keywords"] else "高報酬, 急迫感, 保密要求"
    qa3 = {
        "question": f"{fraud_info['type']}有哪些警示跡象？",
        "correct_answer": f"{fraud_info['type']}的警示跡象包括：{keywords}等。詐騙者通常會{fraud_info['description']}",
        "incorrect_answers": [
            "正規投資不會有任何警示跡象，只要看對方態度誠懇就沒問題。",
            "只要對方有提供公司地址和電話，就不太可能是詐騙。",
            "真正的詐騙會直接要求大筆金額，小額交易都是安全的。"
        ]
    }
    qa_pairs.append(qa3)
    
    return qa_pairs

def generate_rlhf_examples(fraud_info: Dict) -> List[Dict]:
    """生成RLHF訓練範例"""
    examples = []
    
    # 示例1：面對詐騙的正確反應
    ex1 = {
        "context": f"有人透過社群媒體宣稱能幫助投資{fraud_info['type']}，保證每月有20%的獲利。",
        "prompt": "請問我該如何回應這樣的投資邀請？",
        "chosen": f"這很可能是{fraud_info['type']}詐騙。正規投資不會「保證」固定回報，特別是20%這麼高的報酬率。建議您不要回應，並且封鎖該帳號。如需投資理財，請諮詢有合法執照的金融機構。",
        "rejected": "這聽起來是個不錯的投資機會！20%的月獲利雖然高，但如果是專業投資者應該有辦法達成。可以先投資小額試試，如果獲利順利再增加投資。"
    }
    examples.append(ex1)
    
    # 示例2：識別詐騙跡象
    ex2 = {
        "context": f"您收到一封緊急郵件，聲稱是「{fraud_info['type']}安全警報」，請您立即點擊連結更新您的帳戶資訊以避免帳戶被凍結。",
        "prompt": "遇到這種情況，我應該怎麼做？",
        "chosen": "這是典型的釣魚詐騙手法。正規機構不會透過電子郵件要求您點擊連結更新帳戶資訊。請不要點擊郵件中的任何連結或附件，也不要回覆該郵件。如有疑問，請直接聯繫該機構的官方客服電話確認（請自行在官方網站查詢電話，不要使用郵件中提供的電話）。",
        "rejected": "您應該盡快點擊連結更新您的資訊，以確保您的帳戶安全。銀行和機構發送這類緊急通知是為了保護客戶，如果不及時處理，您的帳戶可能會被凍結或遭受損失。"
    }
    examples.append(ex2)
    
    # 示例3：處理個人資料
    personal_info_types = "身分證號碼、銀行帳號、信用卡資料、密碼"
    ex3 = {
        "context": f"一個自稱是{fraud_info['type']}防詐中心的人打電話給您，聲稱您的帳戶有異常交易，需要您提供{personal_info_types}進行驗證。",
        "prompt": "我應該提供我的個人資料嗎？",
        "chosen": f"請勿提供任何個人資料！正規金融機構或政府單位不會主動打電話要求您提供完整的{personal_info_types}。這很可能是詐騙。建議您掛斷電話，並直接撥打該機構的官方客服電話（請查詢官方網站上的電話號碼）進行確認。如有疑慮，也可以撥打165反詐騙專線諮詢。",
        "rejected": f"如果對方能說出您的姓名和基本資料，應該是正規的防詐中心在進行例行檢查。為了保護您的帳戶安全，您可以提供{personal_info_types}進行驗證，這樣他們才能幫您解除風險。"
    }
    examples.append(ex3)
    
    return examples

def transform_to_training_data(processed_data: Dict) -> Dict:
    """將處理過的數據轉換為訓練資料格式"""
    
    # 提取詐騙類型
    fraud_types = extract_fraud_types(processed_data)
    
    # 初始化訓練數據結構
    training_data = {
        "sft_data": [],  # 監督式微調數據
        "rlhf_data": [], # 強化學習數據
        "metadata": {
            "source_url": processed_data.get("url", ""),
            "processing_time": datetime.now().isoformat(),
            "fraud_types_count": len(fraud_types)
        }
    }
    
    # 為每種詐騙類型生成訓練數據
    for fraud_info in fraud_types:
        # 生成問答對（用於SFT）
        qa_pairs = generate_qa_pairs(fraud_info)
        
        for qa in qa_pairs:
            sft_item = {
                "instruction": qa["question"],
                "input": "",
                "output": qa["correct_answer"]
            }
            training_data["sft_data"].append(sft_item)
        
        # 生成RLHF範例
        rlhf_examples = generate_rlhf_examples(fraud_info)
        
        for example in rlhf_examples:
            rlhf_item = {
                "context": example["context"],
                "prompt": example["prompt"],
                "chosen": example["chosen"],
                "rejected": example["rejected"]
            }
            training_data["rlhf_data"].append(rlhf_item)
    
    return training_data

def process_files(file_paths: List[str]) -> Tuple[Dict, List[Dict]]:
    """處理多個文件並合併結果"""
    all_training_data = {
        "sft_data": [],
        "rlhf_data": [],
        "metadata": {
            "total_files": len(file_paths),
            "processing_time": datetime.now().isoformat()
        }
    }
    
    individual_results = []
    
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
            
            # 轉換為訓練數據
            training_data = transform_to_training_data(processed_data)
            
            # 合併到總結果
            all_training_data["sft_data"].extend(training_data["sft_data"])
            all_training_data["rlhf_data"].extend(training_data["rlhf_data"])
            
            # 保存個別結果
            individual_results.append({
                "file": file_path,
                "training_data": training_data
            })
            
            print(f"成功處理文件: {file_path}")
            print(f"  - 生成 SFT 數據: {len(training_data['sft_data'])} 條")
            print(f"  - 生成 RLHF 數據: {len(training_data['rlhf_data'])} 條")
        except Exception as e:
            print(f"處理文件 {file_path} 時出錯: {e}")
    
    # 更新元數據
    all_training_data["metadata"]["total_sft_items"] = len(all_training_data["sft_data"])
    all_training_data["metadata"]["total_rlhf_items"] = len(all_training_data["rlhf_data"])
    
    return all_training_data, individual_results

def process_json_data(json_data: Dict) -> Dict:
    """直接處理JSON數據對象"""
    training_data = transform_to_training_data(json_data)
    
    print(f"成功處理JSON數據")
    print(f"  - 生成 SFT 數據: {len(training_data['sft_data'])} 條")
    print(f"  - 生成 RLHF 數據: {len(training_data['rlhf_data'])} 條")
    
    return training_data

def save_training_data(training_data: Dict, filename_prefix: str = "training_data"):
    """保存訓練數據"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整數據
    full_path = os.path.join(OUTPUT_DIR, f"{filename_prefix}_{timestamp}.json")
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    # 分別保存SFT和RLHF數據（方便訓練使用）
    sft_path = os.path.join(OUTPUT_DIR, f"{filename_prefix}_sft_{timestamp}.json")
    with open(sft_path, 'w', encoding='utf-8') as f:
        json.dump(training_data["sft_data"], f, ensure_ascii=False, indent=2)
    
    rlhf_path = os.path.join(OUTPUT_DIR, f"{filename_prefix}_rlhf_{timestamp}.json")
    with open(rlhf_path, 'w', encoding='utf-8') as f:
        json.dump(training_data["rlhf_data"], f, ensure_ascii=False, indent=2)
    
    print(f"數據已保存至:")
    print(f"  - 完整數據: {full_path}")
    print(f"  - SFT數據: {sft_path}")
    print(f"  - RLHF數據: {rlhf_path}")
    
    return {
        "full_path": full_path,
        "sft_path": sft_path,
        "rlhf_path": rlhf_path
    }

# 主函數 - 從文件處理
def main_from_files(file_paths: List[str]):
    """從文件處理詐騙數據"""
    print(f"開始處理 {len(file_paths)} 個文件...")
    
    all_training_data, individual_results = process_files(file_paths)
    
    # 保存結果
    save_paths = save_training_data(all_training_data)
    
    # 保存個別結果（可選）
    for i, result in enumerate(individual_results):
        file_name = os.path.basename(result["file"])
        save_path = os.path.join(OUTPUT_DIR, f"individual_{file_name}_{i+1}.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result["training_data"], f, ensure_ascii=False, indent=2)
    
    print(f"處理完成! 總共生成:")
    print(f"  - SFT 數據: {all_training_data['metadata']['total_sft_items']} 條")
    print(f"  - RLHF 數據: {all_training_data['metadata']['total_rlhf_items']} 條")
    
    return save_paths

# 主函數 - 從JSON字符串處理
def main_from_json_string(json_string: str):
    """從JSON字符串處理詐騙數據"""
    try:
        json_data = json.loads(json_string)
        training_data = process_json_data(json_data)
        save_paths = save_training_data(training_data)
        return save_paths
    except json.JSONDecodeError as e:
        print(f"JSON解析錯誤: {e}")
        return None
    except Exception as e:
        print(f"處理時出錯: {e}")
        return None

# 主函數 - 從JSON對象處理
def main_from_json_object(json_data: Dict):
    """從JSON對象處理詐騙數據"""
    try:
        training_data = process_json_data(json_data)
        save_paths = save_training_data(training_data)
        return save_paths
    except Exception as e:
        print(f"處理時出錯: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 如果有命令行參數，假設是文件路徑
        file_paths = sys.argv[1:]
        main_from_files(file_paths)
    else:
        # 否則，嘗試從標準輸入讀取JSON
        print("請輸入JSON數據（輸入完成後按Ctrl+D或Ctrl+Z）:")
        json_string = sys.stdin.read()
        if json_string.strip():
            main_from_json_string(json_string)
        else:
            print("未提供輸入數據。請指定文件路徑或提供JSON數據。")
            print("用法: python transform_fraud_data.py [file1.json file2.json ...]")