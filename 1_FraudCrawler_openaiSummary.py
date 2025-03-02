import json
import requests
import os
from datetime import datetime
from tqdm import tqdm
import time

# API密鑰設置
JINA_API_KEY = "jina_2752307cab7a46e29d16c3fcbcdca7e2VPAObQDS2ER66cFvwpmGVIeIN8TG"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # 從環境變量獲取，或手動設置

# 設置輸出目錄
OUTPUT_DIR = "fraud_data/processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_jina_response(jina_response):
    """解析Jina API的回應內容"""
    try:
        # 嘗試解析JSON
        content_json = json.loads(jina_response)
        
        # 提取主要內容
        if "data" in content_json and "content" in content_json["data"]:
            return content_json["data"]["content"]
        else:
            print("警告: Jina回應中未找到內容")
            return jina_response
    except json.JSONDecodeError:
        # 如果不是JSON格式，直接返回原始內容
        print("警告: 無法解析Jina回應為JSON")
        return jina_response

def process_with_openai(content, url):
    """使用OpenAI處理內容"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        prompt = f"""
        以下是從「165全民防騙網」({url})使用Jina API擷取的內容。
        請將此內容整理為結構化資料，包含以下資訊：
        
        1. 網站主題摘要
        2. 主要的詐騙警示訊息
        3. 列出至少3種該網站提及的詐騙類型
        4. 提取預防詐騙的建議
        5. 提取的重要連結與資源
        
        請以JSON格式回應，確保所有內容都是繁體中文。
        
        網頁內容：
        {content}
        """
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "你是一個專業的資料整理助手，專長於提取和分析防詐騙資訊。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        
        # 發送請求到OpenAI
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # 檢查回應
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                structured_content = json.loads(result["choices"][0]["message"]["content"])
                return {
                    "success": True,
                    "structured_data": structured_content,
                    "raw_openai_response": result
                }
            else:
                return {
                    "success": False,
                    "error": "OpenAI回應中未找到內容",
                    "raw_openai_response": result
                }
        else:
            return {
                "success": False,
                "error": f"OpenAI API返回錯誤代碼: {response.status_code}",
                "raw_response": response.text
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"處理內容時出錯: {str(e)}"
        }

def crawl_and_process(url):
    """爬取URL並使用LLM處理內容"""
    # 1. 使用Jina爬取URL
    print(f"使用Jina API爬取: {url}")
    headers = {
        'Authorization': f'Bearer {JINA_API_KEY}'
    }
    jina_url = f'https://r.jina.ai/{url}'
    
    try:
        response = requests.get(jina_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {
                "url": url,
                "success": False,
                "error": f"Jina API返回錯誤代碼: {response.status_code}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 2. 解析Jina回應
        jina_content = response.text
        parsed_content = parse_jina_response(jina_content)
        
        # 3. 如果OpenAI API密鑰可用，使用OpenAI處理
        if OPENAI_API_KEY:
            print(f"使用OpenAI處理內容...")
            openai_result = process_with_openai(parsed_content, url)
            
            # 組合最終結果
            result = {
                "url": url,
                "jina_url": jina_url,
                "success": True,
                "jina_raw_response": jina_content,
                "parsed_content": parsed_content[:1000] + "..." if len(parsed_content) > 1000 else parsed_content,
                "openai_processing": openai_result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 如果沒有OpenAI API密鑰，只返回Jina結果
            print("警告: 未提供OpenAI API密鑰，只返回Jina結果")
            result = {
                "url": url,
                "jina_url": jina_url,
                "success": True,
                "jina_raw_response": jina_content,
                "parsed_content": parsed_content,
                "timestamp": datetime.now().isoformat()
            }
        
        return result
    
    except Exception as e:
        print(f"處理URL時出錯: {e}")
        return {
            "url": url,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def process_jina_result(jina_result):
    """處理已經獲取的Jina結果"""
    try:
        # 解析content字段
        content = jina_result["content"]
        parsed_content = parse_jina_response(content)
        
        # 使用OpenAI處理
        if OPENAI_API_KEY:
            print(f"使用OpenAI處理內容...")
            openai_result = process_with_openai(parsed_content, jina_result["url"])
            
            # 組合最終結果
            result = {
                "url": jina_result["url"],
                "success": True,
                "parsed_content": parsed_content[:1000] + "..." if len(parsed_content) > 1000 else parsed_content,
                "openai_processing": openai_result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 如果沒有OpenAI API密鑰，只返回解析結果
            print("警告: 未提供OpenAI API密鑰，只返回解析結果")
            result = {
                "url": jina_result["url"],
                "success": True,
                "parsed_content": parsed_content,
                "timestamp": datetime.now().isoformat()
            }
        
        return result
    
    except Exception as e:
        print(f"處理Jina結果時出錯: {e}")
        return {
            "url": jina_result.get("url", "unknown"),
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def save_result(result, prefix="processed"):
    """保存處理結果"""
    try:
        # 創建文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # 保存JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"已保存結果到: {filepath}")
        return filepath
    
    except Exception as e:
        print(f"保存結果時出錯: {e}")
        return None

def main_crawl_and_process(urls):
    """主函數 - 爬取並處理多個URL"""
    results = []
    
    print(f"開始處理 {len(urls)} 個URL...")
    with tqdm(total=len(urls)) as pbar:
        for i, url in enumerate(urls):
            pbar.set_description(f"處理 {url}")
            
            # 爬取並處理URL
            result = crawl_and_process(url)
            results.append(result)
            
            # 保存單個結果
            save_result(result, prefix=f"url_{i+1}")
            
            # 更新進度
            pbar.update(1)
            pbar.set_postfix({"成功": result["success"]})
            
            # 暫停以避免API限制
            if i < len(urls) - 1:
                time.sleep(1)
    
    # 保存所有結果
    all_results = {
        "total_urls": len(urls),
        "successful_processes": sum(1 for r in results if r["success"]),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    save_result(all_results, prefix="all_results")
    
    print(f"處理完成! 成功: {all_results['successful_processes']}/{all_results['total_urls']}")
    return results

def main_process_existing(jina_results):
    """主函數 - 處理已存在的Jina結果"""
    results = []
    
    print(f"開始處理 {len(jina_results)} 個已獲取的Jina結果...")
    with tqdm(total=len(jina_results)) as pbar:
        for i, jina_result in enumerate(jina_results):
            url = jina_result.get("url", f"result_{i+1}")
            pbar.set_description(f"處理 {url}")
            
            # 處理Jina結果
            result = process_jina_result(jina_result)
            results.append(result)
            
            # 保存單個結果
            save_result(result, prefix=f"processed_{i+1}")
            
            # 更新進度
            pbar.update(1)
            pbar.set_postfix({"成功": result["success"]})
            
            # 暫停以避免API限制
            if i < len(jina_results) - 1:
                time.sleep(1)
    
    # 保存所有結果
    all_results = {
        "total_items": len(jina_results),
        "successful_processes": sum(1 for r in results if r["success"]),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    save_result(all_results, prefix="all_processed_results")
    
    print(f"處理完成! 成功: {all_results['successful_processes']}/{all_results['total_items']}")
    return results

# 使用範例
if __name__ == "__main__":
    # 設置OpenAI API密鑰
    if not OPENAI_API_KEY:
        OPENAI_API_KEY = input("請輸入您的OpenAI API密鑰: ")
    
    # 選擇模式
    print("選擇操作模式:")
    print("1. 爬取新URL並處理")
    print("2. 處理已獲取的Jina結果")
    
    choice = input("請選擇 (1/2): ")
    
    if choice == "1":
        # 爬取新URL
        urls_to_process = [
            "https://165.npa.gov.tw/#/",
            "https://165.npa.gov.tw/#/articles/C",
            "https://165.npa.gov.tw/#/articles/1",
            "https://165.npa.gov.tw/#/articles/A",
            "https://165.npa.gov.tw/#/articles/6"
        ]
        main_crawl_and_process(urls_to_process)
    
    elif choice == "2":
    # 處理已獲取的結果
        print("請輸入包含Jina結果的JSON文件路徑:")
        file_path = input().strip()
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    jina_results = json.load(f)
                
                if isinstance(jina_results, dict):
                    # 如果文件包含單個結果
                    jina_results = [jina_results]
                
                main_process_existing(jina_results)
            else:
                print(f"錯誤: 找不到文件 '{file_path}'")
        except json.JSONDecodeError:
            print("錯誤: 無法解析JSON文件")
        except Exception as e:
            print(f"錯誤: {str(e)}")