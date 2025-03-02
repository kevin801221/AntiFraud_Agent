import json
import os
import glob
from pathlib import Path

def read_video_summary(file_path):
    """讀取視頻摘要文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def read_frame_analyses(file_path):
    """讀取幀分析文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_training_examples(summary, frames):
    """創建訓練數據範例"""
    examples = []
    
    # 從摘要創建一般性的問答
    summary_example = {
        "messages": [
            {"role": "system", "content": "你是一個專業的反詐騙顧問，專門幫助人們識別和預防線上遊戲詐騙。"},
            {"role": "user", "content": "請告訴我關於線上遊戲詐騙的主要類型和預防方法。"},
            {"role": "assistant", "content": summary},
            {"role": "user", "content": "這些詐騙手法聽起來很危險，我該如何保護自己？"},
            {"role": "assistant", "content": "根據分析，以下是保護自己的關鍵步驟：\n\n"
                                          "1. 認清官方管道：\n"
                                          "   - 只通過遊戲官方商店購買道具\n"
                                          "   - 不要相信非官方的促銷活動\n"
                                          "   - 確認所有交易都在遊戲內進行\n\n"
                                          "2. 保護個人信息：\n"
                                          "   - 永遠不要分享遊戲序號\n"
                                          "   - 不要告訴他人帳號密碼\n"
                                          "   - 啟用雙重驗證\n\n"
                                          "3. 提高警覺性：\n"
                                          "   - 對限時優惠要特別小心\n"
                                          "   - 不要相信免費道具的承諾\n"
                                          "   - 避免點擊不明連結\n\n"
                                          "4. 及時求助：\n"
                                          "   - 遇到可疑情況立即告訴父母或老師\n"
                                          "   - 可以撥打165反詐騙專線\n"
                                          "   - 向遊戲官方回報可疑行為\n\n"
                                          "記住：寧可錯過一個「優惠」，也不要冒險損失帳號或金錢！"}
        ]
    }
    examples.append(summary_example)
    
    # 從每個幀分析創建具體場景的問答
    for frame in frames:
        if not frame.get('description'):
            continue
            
        frame_example = {
            "messages": [
                {"role": "system", "content": "你是一個專業的反詐騙顧問，專門幫助人們識別和預防線上遊戲詐騙。"},
                {"role": "user", "content": "在遊戲中遇到這種情況該怎麼辦？" + frame['description'].split('\n')[0]},
                {"role": "assistant", "content": frame['description']},
                {"role": "user", "content": "這種情況看起來很誘人，但我該如何判斷是否為詐騙？"},
                {"role": "assistant", "content": "根據這個場景，以下是判斷和應對的方法：\n\n"
                                              + frame['description'].split('\n\n')[1] if '\n\n' in frame['description'] 
                                              else frame['description']}
            ]
        }
        examples.append(frame_example)
    
    return examples

def main():
    video_analysis_dir = '/Users/kevinluo/application/Fraud_rebuild/output/video_analysis'
    output_file = '/Users/kevinluo/application/Fraud_rebuild/fraud_data/03_training_data/video_analysis_training.jsonl'
    
    all_examples = []
    
    # 遍歷所有視頻分析目錄
    for video_dir in glob.glob(os.path.join(video_analysis_dir, '*/')):
        summary_file = os.path.join(video_dir, 'video_summary.txt')
        frames_file = os.path.join(video_dir, 'frame_analyses.json')
        
        if not os.path.exists(summary_file) or not os.path.exists(frames_file):
            continue
            
        summary = read_video_summary(summary_file)
        frames = read_frame_analyses(frames_file)
        
        examples = create_training_examples(summary, frames)
        all_examples.extend(examples)
    
    # 寫入訓練數據
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in all_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    # 將新數據添加到現有的 DPO 訓練數據文件
    dpo_file = '/Users/kevinluo/application/Fraud_rebuild/fraud_data/03_training_data/dpo_training_data_openai.jsonl'
    with open(dpo_file, 'a', encoding='utf-8') as f:
        for example in all_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"已處理 {len(all_examples)} 個訓練範例")

if __name__ == '__main__':
    main()
