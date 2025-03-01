#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module: 3_training_data_generator.py
Description: 定義 TrainingDataGenerator 類別，用於生成訓練資料（SFT 與 RLHF 格式）。
"""

import re
from datetime import datetime
from tqdm import tqdm
from core.utils import log

class TrainingDataGenerator:
    """
    生成訓練資料的類別，包含：
      - SFT 資料：問答對形式。
      - RLHF 資料：包含上下文、提示、正確與拒絕回答的範例。
    """
    def __init__(self):
        self.fraud_keywords = [
            "詐騙", "假冒", "投資", "博弈", "帳戶", "個資", "資料", "冒用", 
            "假的", "騙局", "高報酬", "高獲利", "中獎", "退款", "退稅",
            "綁架", "勒索", "贖金", "緊急", "解除", "警示", "銀行", "轉帳"
        ]

    def _extract_keywords(self, text: str) -> list:
        """
        從文字中利用正則表達式提取關鍵字。

        Args:
            text (str): 要處理的文字。

        Returns:
            list: 提取出的關鍵字列表。
        """
        fraud_related_words = [
            "詐騙", "假冒", "投資", "博弈", "帳戶", "個資", "資料", "冒用", 
            "假的", "騙局", "高報酬", "高獲利", "中獎", "退款", "退稅",
            "綁架", "勒索", "贖金", "緊急", "解除", "警示", "銀行", "轉帳",
            "警察", "公務員", "檢察官", "法院", "監管", "監控", "監視", "追蹤"
        ]
        words = re.findall(r'\w+', text)
        keywords = [word for word in words if word in fraud_related_words or len(word) >= 3]
        return keywords

    def _generate_qa_pairs(self, fraud_info: dict) -> list:
        """
        根據詐騙資訊生成 SFT 問答對。

        Args:
            fraud_info (dict): 包含詐騙類型與相關描述的資訊。

        Returns:
            list: 問答對列表，每筆包含問題、正確答案與錯誤選項。
        """
        qa_pairs = []
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

    def _generate_rlhf_examples(self, fraud_info: dict) -> list:
        """
        根據詐騙資訊生成 RLHF 訓練範例。

        Args:
            fraud_info (dict): 包含詐騙相關資訊的字典。

        Returns:
            list: RLHF 範例列表，每筆包含上下文、提示、正確與拒絕回答。
        """
        examples = []
        ex1 = {
            "context": f"有人透過社群媒體宣稱能幫助投資{fraud_info['type']}，保證每月有20%的獲利。",
            "prompt": "請問我該如何回應這樣的投資邀請？",
            "chosen": f"這很可能是{fraud_info['type']}詐騙。正規投資不會「保證」固定回報，特別是20%這麼高的報酬率。建議您不要回應，並且封鎖該帳號。如需投資理財，請諮詢有合法執照的金融機構。",
            "rejected": "這聽起來是個不錯的投資機會！20%的月獲利雖然高，但如果是專業投資者應該有辦法達成。可以先投資小額試試，如果獲利順利再增加投資。"
        }
        examples.append(ex1)
        ex2 = {
            "context": f"您收到一封緊急郵件，聲稱是「{fraud_info['type']}安全警報」，請您立即點擊連結更新您的帳戶資訊以避免帳戶被凍結。",
            "prompt": "遇到這種情況該怎麼辦？",
            "chosen": f"這是典型的{fraud_info['type']}詐騙手法。正規機構不會透過電子郵件要求您緊急更新帳戶資訊。請勿點擊任何連結，也不要提供任何個人資料。如有疑慮，請直接聯繫您的銀行或相關機構確認。",
            "rejected": "雖然看起來有點可疑，但為了安全起見，還是先點進去看看是什麼情況。如果真的要輸入資料，我會特別小心，只提供必要的資訊。"
        }
        examples.append(ex2)
        return examples

    def _extract_fraud_types(self, data: dict) -> list:
        """
        從 OpenAI 處理後的結構化資料中提取詐騙類型資訊，
        若未提供則使用預設的網路詐騙資訊作為備援。

        Args:
            data (dict): 處理後的結構化資料。

        Returns:
            list: 詐騙類型資訊的列表，每筆為一個字典。
        """
        fraud_types = []
        if "openai_processing" in data and data["openai_processing"].get("success", False):
            structured_data = data["openai_processing"].get("structured_data", {})
            if "詐騙類型" in structured_data and isinstance(structured_data["詐騙類型"], list):
                for fraud_type in structured_data["詐騙類型"]:
                    fraud_info = {
                        "type": fraud_type,
                        "description": structured_data.get("主要的詐騙警示訊息", ""),
                        "prevention": structured_data.get("預防詐騙的建議", ""),
                        "alert_keywords": [],
                        "examples": []
                    }
                    keywords = re.findall(r'\w+', fraud_type)
                    if "主要的詐騙警示訊息" in structured_data:
                        desc_keywords = self._extract_keywords(structured_data["主要的詐騙警示訊息"])
                        keywords.extend(desc_keywords)
                    fraud_info["alert_keywords"] = list(set([k for k in keywords if len(k) > 1]))
                    fraud_info["examples"].append({
                        "scenario": f"{fraud_type}的典型情況",
                        "context": f"詐騙者利用{fraud_type}手法進行詐騙",
                        "fraudster_message": f"這是一個{fraud_type}的示例詐騙信息",
                        "correct_response": "這是詐騙，我應該拒絕並舉報"
                    })
                    fraud_types.append(fraud_info)
            elif structured_data:
                fraud_info = {
                    "type": "一般詐騙",
                    "description": structured_data.get("主要的詐騙警示訊息", "未提供詳細資訊"),
                    "prevention": structured_data.get("預防詐騙的建議", "請保持警覺，遇到可疑情況請聯繫165反詐騙專線"),
                    "alert_keywords": self._extract_keywords(structured_data.get("網站主題摘要", "")),
                    "examples": [{
                        "scenario": "一般詐騙情況",
                        "context": "詐騙者嘗試騙取個人資料或金錢",
                        "fraudster_message": "這是一個詐騙示例信息",
                        "correct_response": "這是詐騙，我應該拒絕並舉報"
                    }]
                }
                fraud_types.append(fraud_info)
        else:
            fraud_info = {
                "type": "網路詐騙",
                "description": "網路詐騙透過各種手法騙取個人資料或金錢",
                "prevention": "不要輕易相信網路上的陌生人或訊息，保護個人資料，遇到可疑情況請聯繫165反詐騙專線",
                "alert_keywords": ["詐騙", "個資", "騙局", "錢", "緊急"],
                "examples": [{
                    "scenario": "網路詐騙典型情況",
                    "context": "詐騙者透過網路騙取個人資料或金錢",
                    "fraudster_message": "這是一個網路詐騙示例信息",
                    "correct_response": "這是詐騙，我應該拒絕並舉報"
                }]
            }
            fraud_types.append(fraud_info)
        return fraud_types

    def _transform_to_training_data(self, processed_result: dict) -> dict:
        """
        將單筆處理後的資料轉換為訓練資料（包含 SFT 與 RLHF 格式）。

        Args:
            processed_result (dict): 處理後的資料。

        Returns:
            dict: 轉換後的訓練資料，包含 sft_data 與 rlhf_data。
        """
        fraud_types = self._extract_fraud_types(processed_result)
        training_data = {
            "sft_data": [],
            "rlhf_data": [],
            "metadata": {
                "source_url": processed_result.get("url", ""),
                "timestamp": datetime.now().isoformat(),
                "fraud_types_count": len(fraud_types)
            }
        }
        for fraud_info in fraud_types:
            qa_pairs = self._generate_qa_pairs(fraud_info)
            for qa in qa_pairs:
                sft_item = {
                    "instruction": qa["question"],
                    "input": "",
                    "output": qa["correct_answer"]
                }
                training_data["sft_data"].append(sft_item)
            rlhf_examples = self._generate_rlhf_examples(fraud_info)
            for example in rlhf_examples:
                rlhf_item = {
                    "context": example["context"],
                    "prompt": example["prompt"],
                    "chosen": example["chosen"],
                    "rejected": example["rejected"]
                }
                training_data["rlhf_data"].append(rlhf_item)
        return training_data

    def generate_training_data(self, processed_data: dict) -> dict:
        """
        從多筆處理結果中生成綜合訓練資料。

        Args:
            processed_data (dict): 包含所有處理結果的字典。

        Returns:
            dict: 包含 SFT 與 RLHF 資料以及統計資訊的綜合訓練資料。
        """
        results = processed_data.get("results", [])
        log(f"Generating training data from {len(results)} processed results...")
        combined_training_data = {
            "sft_data": [],
            "rlhf_data": [],
            "metadata": {
                "total_items": len(results),
                "timestamp": datetime.now().isoformat()
            }
        }
        successful_items = 0
        for result in tqdm(results, desc="Generating training data"):
            if result.get("success", False):
                training_data = self._transform_to_training_data(result)
                combined_training_data["sft_data"].extend(training_data["sft_data"])
                combined_training_data["rlhf_data"].extend(training_data["rlhf_data"])
                successful_items += 1
        combined_training_data["metadata"]["successful_items"] = successful_items
        combined_training_data["metadata"]["total_sft_items"] = len(combined_training_data["sft_data"])
        combined_training_data["metadata"]["total_rlhf_items"] = len(combined_training_data["rlhf_data"])
        log(f"Training data generation complete!")
        log(f"Generated {combined_training_data['metadata']['total_sft_items']} SFT items")
        log(f"Generated {combined_training_data['metadata']['total_rlhf_items']} RLHF items")
        return combined_training_data