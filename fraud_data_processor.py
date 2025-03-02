import json
import os
from datetime import datetime
from typing import Dict, List, Any
import requests
from dotenv import load_dotenv
import logging
import asyncio
from pathlib import Path
import pandas as pd
import getpass
import ssl
import warnings

# 忽略SSL警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# 設置日誌
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# ANSI顏色碼用於日誌輸出
PINK = "\033[95m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET_COLOR = "\033[0m"

class FraudDataProcessor:
    def __init__(self):
        load_dotenv()
        # 獲取API密鑰
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.jina_api_key = os.getenv('JINA_API_KEY')  # 如果需要Jina API密鑰
        
        if not self.openai_api_key:
            logging.warning("沒有找到OPENAI_API_KEY環境變量")
        
        self.crawled_data_dir = Path('fraud_data/crawled_data')
        self.training_data_dir = Path('fraud_data/training')
        
        # 確保目錄存在
        self.crawled_data_dir.mkdir(parents=True, exist_ok=True)
        self.training_data_dir.mkdir(parents=True, exist_ok=True)

    def load_crawled_data(self) -> List[Dict]:
        """載入所有爬取的資料"""
        all_data = []
        for file in self.crawled_data_dir.glob('fraud_data_*.json'):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.append(data)
                logging.info(f"Loaded data from {file}")
            except Exception as e:
                logging.error(f"Error loading {file}: {e}")
        return all_data

    def beautifulsoup_web_scrape_url(self, url):
        """使用BeautifulSoup爬取網頁內容"""
        try:
            response = requests.get(url)
            response.raise_for_status()  # 檢查請求是否成功
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            return str(soup)
        except Exception as e:
            logging.error(f"BeautifulSoup爬取失敗: {e}")
            return f"爬取失敗: {str(e)}"

    def jinai_readerapi_web_scraper(self, url, verify_ssl=True):
        """使用Jina Reader API爬取網頁內容，解決亂碼問題"""
        headers = {"Accept": "application/json"}
        try:
            response = requests.get(f"https://r.jina.ai/{url}", headers=headers, verify=verify_ssl)
            return response.text
        except requests.exceptions.SSLError:
            if verify_ssl:
                logging.warning("SSL驗證失敗，嘗試不驗證SSL...")
                return self.jinai_readerapi_web_scraper(url, verify_ssl=False)
            else:
                logging.error(f"連接到r.jina.ai時SSL錯誤，即使不驗證也失敗")
                return f"無法連接到Jina API: SSL證書驗證失敗"
        except Exception as e:
            logging.error(f"Jina Reader API錯誤: {e}")
            return f"Jina API錯誤: {str(e)}"

    def jina_readerapi_search(self, query, verify_ssl=True):
        """使用Jina Reader API搜索內容"""
        try:
            full_url = f"https://s.jina.ai/{query}"
            response = requests.get(full_url, verify=verify_ssl)
            return response.text
        except requests.exceptions.SSLError:
            if verify_ssl:
                logging.warning("SSL驗證失敗，嘗試不驗證SSL...")
                return self.jina_readerapi_search(query, verify_ssl=False)
            else:
                logging.error(f"連接到s.jina.ai時SSL錯誤，即使不驗證也失敗")
                return f"無法連接到Jina搜索API: SSL證書驗證失敗"
        except Exception as e:
            logging.error(f"Jina搜索API錯誤: {e}")
            return f"Jina搜索API錯誤: {str(e)}"

    def jina_readerapi_grounding(self, description, verify_ssl=True):
        """使用Jina Reader API進行資訊驗證"""
        headers = {}
        if self.jina_api_key:
            headers["Authorization"] = f"Bearer {self.jina_api_key}"
        else:
            api_key = getpass.getpass("請輸入您的Jina API Key: ")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
        try:
            full_url = f"https://g.jina.ai/{description}"
            response = requests.get(full_url, headers=headers, verify=verify_ssl)
            return response.text
        except requests.exceptions.SSLError:
            if verify_ssl:
                logging.warning("SSL驗證失敗，嘗試不驗證SSL...")
                return self.jina_readerapi_grounding(description, verify_ssl=False)
            else:
                logging.error(f"連接到g.jina.ai時SSL錯誤，即使不驗證也失敗")
                return f"無法連接到Jina Grounding API: SSL證書驗證失敗"
        except Exception as e:
            logging.error(f"Jina Grounding API錯誤: {e}")
            return f"Jina Grounding API錯誤: {str(e)}"

    async def process_content_with_gpt4o(self, content: str) -> Dict:
        """使用 GPT-4o 處理內容並生成結構化資料"""
        try:
            prompt = f"""請分析以下的反詐騙相關內容，並生成適合用於訓練反詐騙AI模型的資料。
            請提供以下格式的輸出：
            1. 詐騙類型
            2. 詐騙手法描述（簡潔）
            3. 預防方法
            4. 關鍵警示詞
            5. 生成5個問答對（包含正確答案和錯誤答案）
            
            內容如下：
            {content}
            
            請以JSON格式輸出，確保所有內容都是繁體中文。
            """
            
            # 使用OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "你是一個專業的反詐騙訓練資料生成助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"API錯誤: {response.status_code} - {response.text}")
            
            response_data = response.json()
            
            # 解析 JSON 回應
            try:
                return json.loads(response_data["choices"][0]["message"]["content"])
            except:
                return {
                    "error": "無法解析GPT-4o的回應", 
                    "raw_response": response_data["choices"][0]["message"]["content"]
                }
            
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return {"error": str(e)}

    async def enhance_with_gpt4o(self, initial_output: Dict) -> Dict:
        """使用 GPT-4o 增強處理後的輸出"""
        try:
            prompt = f"""基於以下的反詐騙資料，請生成更多的訓練範例和情境：
            
            原始資料：
            {json.dumps(initial_output, ensure_ascii=False, indent=2)}
            
            請生成：
            1. 5個額外的相似詐騙情境
            2. 每個情境的可能變體
            3. 適合RLHF訓練的人類反饋範例
            
            請以JSON格式輸出，確保所有內容都是繁體中文。
            """
            
            # 使用OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "你是一個專業的反詐騙訓練資料生成助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"API錯誤: {response.status_code} - {response.text}")
            
            response_data = response.json()
            
            # 解析 JSON 回應
            try:
                enhanced_data = json.loads(response_data["choices"][0]["message"]["content"])
                return {**initial_output, **enhanced_data}
            except:
                return {**initial_output, "openai_error": "無法解析GPT-4o的回應"}
            
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return {**initial_output, "openai_error": str(e)}

    async def process_image_with_gpt4o(self, image_url: str, caption: str = "這是什麼詐騙圖片？") -> Dict:
        """處理詐騙相關圖片"""
        try:
            # 使用OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": caption},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                }
                            },
                        ],
                    }
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"API錯誤: {response.status_code} - {response.text}")
            
            response_data = response.json()
            
            return {
                "image_url": image_url,
                "analysis": response_data["choices"][0]["message"]["content"]
            }
        except Exception as e:
            logging.error(f"Image processing error: {e}")
            return {"error": str(e), "image_url": image_url}

    async def enrich_content_with_jina(self, query: str, content: str) -> Dict:
        """使用Jina搜索API擴充內容的背景資訊"""
        try:
            # 先使用Jina搜索相關資訊
            search_results = self.jina_readerapi_search(query)
            logging.info(f"{PINK}Jina搜索結果:{RESET_COLOR}")
            logging.info(f"{CYAN}{search_results[:500]}...{RESET_COLOR}")
            
            # 將搜索結果與原內容結合後送給GPT-4o處理
            enriched_prompt = f"""
            原始內容：
            {content}
            
            相關背景資訊：
            {search_results}
            
            請結合以上資訊，豐富對這個詐騙手法的描述和分析。
            """
            
            # 使用GPT-4o處理
            enriched_content = await self.process_content_with_gpt4o(enriched_prompt)
            return {
                "original_content": content,
                "jina_search_query": query,
                "jina_search_results": search_results,
                "enriched_content": enriched_content
            }
        except Exception as e:
            logging.error(f"Jina enrichment error: {e}")
            return {"error": str(e), "original_content": content}

    def verify_content_with_jina(self, content: str) -> Dict:
        """使用Jina Grounding API驗證內容的真實性"""
        try:
            verification_result = self.jina_readerapi_grounding(content)
            logging.info(f"{YELLOW}Jina驗證結果:{RESET_COLOR}")
            logging.info(f"{CYAN}{verification_result}{RESET_COLOR}")
            
            return {
                "content": content,
                "verification_result": verification_result
            }
        except Exception as e:
            logging.error(f"Jina verification error: {e}")
            return {"error": str(e), "content": content}

    def format_for_training(self, processed_data: List[Dict]) -> Dict[str, Any]:
        """將處理後的資料格式化為訓練資料集"""
        sft_data = []  # Supervised Fine-tuning Data
        rlhf_data = [] # RLHF Training Data
        
        for data in processed_data:
            if "error" in data:
                continue
                
            # SFT 資料
            if "qa_pairs" in data:
                for qa in data["qa_pairs"]:
                    sft_data.append({
                        "instruction": qa["question"],
                        "input": "",
                        "output": qa["correct_answer"]
                    })
            
            # RLHF 資料
            if "scenarios" in data:
                for scenario in data["scenarios"]:
                    rlhf_data.append({
                        "prompt": scenario["description"],
                        "chosen": scenario["correct_response"],
                        "rejected": scenario["incorrect_response"]
                    })
        
        return {
            "sft_data": sft_data,
            "rlhf_data": rlhf_data
        }

    def save_training_data(self, training_data: Dict[str, Any]):
        """儲存訓練資料"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 儲存為 JSON
        for data_type, data in training_data.items():
            filename = f"{data_type}_{timestamp}.json"
            filepath = self.training_data_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"Saved {data_type} to {filepath}")
        
        # 生成統計資訊
        stats = {
            "timestamp": timestamp,
            "sft_samples": len(training_data["sft_data"]),
            "rlhf_samples": len(training_data["rlhf_data"]),
            "total_samples": len(training_data["sft_data"]) + len(training_data["rlhf_samples"])
        }
        
        stats_file = self.training_data_dir / f"dataset_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logging.info(f"Saved statistics to {stats_file}")

    async def crawl_website(self, url, category):
        """爬取指定網站的內容並儲存"""
        try:
            # 先用BeautifulSoup爬取
            content = self.beautifulsoup_web_scrape_url(url)
            
            # 如果內容無法正確解析，使用Jina Reader API
            if "爬取失敗" in content:
                content = self.jinai_readerapi_web_scraper(url)
            
            result = {
                "url": url,
                "category": category,
                "raw_content": content,
                "status": 200,
                "timestamp": datetime.now().isoformat()
            }
            
            # 嘗試解析並結構化內容
            try:
                # 簡單的結構化處理
                structured_data = {
                    "title": "",
                    "main_content": content[:5000],  # 只取前5000字元
                    "category": category,
                    "source_url": url,
                    "extracted_patterns": self.extract_patterns(content),
                    "metadata": {
                        "crawl_time": datetime.now().isoformat(),
                        "content_length": len(content)
                    }
                }
                result["structured_data"] = structured_data
            except Exception as e:
                logging.error(f"結構化處理錯誤: {e}")
            
            return result
        except Exception as e:
            logging.error(f"爬取{url}時出錯: {e}")
            return {
                "url": url,
                "category": category,
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }

    def extract_patterns(self, content):
        """從內容中提取關鍵模式，如電話號碼、LINE ID等"""
        import re
        
        # 提取電話號碼
        phone_pattern = r"\b(?:\+?886|0)[-\s]?[2-9](?:[-\s]?\d{1,4}){2,3}\b"
        phones = re.findall(phone_pattern, content)
        
        # 提取LINE ID
        line_pattern = r"LINE[:\s]*(ID)?[:\s]*([a-zA-Z0-9_\-.]+)"
        line_matches = re.findall(line_pattern, content)
        line_ids = [match[1] if match[1] else match[0] for match in line_matches]
        
        # 提取URL
        url_pattern = r"https?://[^\s)\"']+"
        urls = re.findall(url_pattern, content)
        
        # 提取詐騙關鍵詞出現次數
        fraud_keywords = {
            "詐騙": len(re.findall(r"詐騙", content)),
            "假投資": len(re.findall(r"假投資", content)),
            "假冒": len(re.findall(r"假冒", content)),
            "詐欺": len(re.findall(r"詐欺", content))
        }
        
        return {
            "phone_numbers": phones,
            "line_ids": line_ids,
            "urls": urls,
            "fraud_keywords": fraud_keywords
        }

    async def crawl_all_sources(self):
        """爬取所有來源並保存"""
        # 定義爬取來源
        sources = {
            "最新詐騙手法": [
                {"url": "https://165.npa.gov.tw/#/articles/C", "category": "詐騙手法"},
                {"url": "https://165.npa.gov.tw/#/articles/1", "category": "新聞快訊"},
                {"url": "https://165.npa.gov.tw/#/articles/A", "category": "常見問答"}
            ],
            "防詐資訊": [
                {"url": "https://165.npa.gov.tw/#/articles/6", "category": "防詐資訊"},
                {"url": "https://cib.npa.gov.tw/ch/app/news/list?module=news_list&type=2", "category": "警方公告"},
                {"url": "https://www.npa.gov.tw/ch/app/news/list?module=news_list&type=2", "category": "警政新聞"}
            ]
        }
        
        # 結果字典
        results = {}
        
        # 爬取每個分類下的來源
        for category, urls in sources.items():
            category_results = []
            for source in urls:
                result = await self.crawl_website(source["url"], source["category"])
                category_results.append(result)
            results[category] = category_results
        
        # 保存爬取結果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"fraud_data_{timestamp}.json"
        filepath = self.crawled_data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logging.info(f"已保存爬取結果到 {filepath}")
        return results

    async def process_all_data(self):
        """處理所有爬取的資料"""
        crawled_data = self.load_crawled_data()
        processed_data = []
        
        # 如果沒有已爬取的資料，先爬取
        if not crawled_data:
            logging.info("沒有找到已爬取的資料，開始新的爬取...")
            await self.crawl_all_sources()
            crawled_data = self.load_crawled_data()
        
        for data_file in crawled_data:
            for category, items in data_file.items():
                for item in items:
                    if isinstance(item, dict):
                        logging.info(f"Processing item from category: {category}")
                        
                        # 處理內容文本
                        if 'raw_content' in item and len(item['raw_content']) > 0:
                            content = item['raw_content']
                            
                            # 先使用Jina擴充內容
                            if 'category' in item:
                                query = f"{item['category']} 詐騙案例"
                                enriched_data = await self.enrich_content_with_jina(query, content)
                                
                                # 如果Jina擴充成功，使用擴充後的內容
                                content_to_process = enriched_data.get('enriched_content', content)
                                if isinstance(content_to_process, dict) and 'error' in content_to_process:
                                    content_to_process = content
                            else:
                                content_to_process = content
                            
                            # 使用GPT-4o處理內容
                            initial_output = await self.process_content_with_gpt4o(content_to_process)
                            
                            # 使用GPT-4o增強輸出
                            enhanced_output = await self.enhance_with_gpt4o(initial_output)
                            
                            # 如果內容涉及事實性陳述，使用Jina驗證
                            if ('詐騙' in content or '詐欺' in content) and len(content) < 2000:
                                verification = self.verify_content_with_jina(json.dumps(enhanced_output, ensure_ascii=False))
                                enhanced_output['verification'] = verification
                            
                            processed_data.append(enhanced_output)
                        
                        # 如果有結構化資料，也處理它
                        elif 'structured_data' in item and isinstance(item['structured_data'], dict):
                            struct_data = item['structured_data']
                            if 'main_content' in struct_data and len(struct_data['main_content']) > 0:
                                # 處理結構化內容
                                initial_output = await self.process_content_with_gpt4o(struct_data['main_content'])
                                enhanced_output = await self.enhance_with_gpt4o(initial_output)
                                processed_data.append(enhanced_output)
                        
                        # 如果有圖片URL，也處理圖片
                        if 'image_url' in item and item['image_url']:
                            image_analysis = await self.process_image_with_gpt4o(item['image_url'])
                            processed_data.append(image_analysis)
        
        # 如果沒有處理到任何資料，可能是原始資料有問題
        if not processed_data:
            logging.warning("沒有處理到任何資料，可能是原始資料格式問題")
            # 嘗試查看原始資料結構
            for data_file in crawled_data:
                logging.info(f"原始資料結構: {list(data_file.keys())}")
                for category, items in data_file.items():
                    if isinstance(items, list) and len(items) > 0:
                        sample_item = items[0]
                        logging.info(f"樣本項目結構: {list(sample_item.keys() if isinstance(sample_item, dict) else [])}")
        
        # 格式化為訓練資料
        training_data = self.format_for_training(processed_data)
        
        # 儲存訓練資料
        self.save_training_data(training_data)
        
        return training_data

async def main():
    processor = FraudDataProcessor()
    
    # 爬取最新詐騙資料
    logging.info(f"{YELLOW}開始爬取最新詐騙資料...{RESET_COLOR}")
    await processor.crawl_all_sources()
    
    # 簡單的Jina API演示
    demo_url = "https://www.165.gov.tw/index.aspx"
    print(f"{YELLOW}使用Jina Reader API爬取內容:{RESET_COLOR}")
    content = processor.jinai_readerapi_web_scraper(demo_url)
    print(f"{CYAN}爬取結果(前500字符):{RESET_COLOR}")
    print(content[:500] + "..." if len(content) > 500 else content)
    
    print(f"\n{YELLOW}使用Jina Search API搜索:{RESET_COLOR}")
    search_result = processor.jina_readerapi_search("最新電信詐騙手法")
    print(f"{PINK}搜索結果(前500字符):{RESET_COLOR}")
    print(search_result[:500] + "..." if len(search_result) > 500 else search_result)
    
    # 完整處理流程
    print(f"\n{YELLOW}開始處理所有爬取的詐騙資料:{RESET_COLOR}")
    await processor.process_all_data()

if __name__ == "__main__":
    asyncio.run(main())