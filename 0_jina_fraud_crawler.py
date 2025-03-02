#只有一個
# import requests  
# url = 'https://r.jina.ai/https://165.npa.gov.tw/#/' 
# headers = {'Authorization': 'Bearer jina_2752307cab7a46e29d16c3fcbcdca7e2VPAObQDS2ER66cFvwpmGVIeIN8TG'} 
# response = requests.get(url, headers=headers) 
# print(response.text) 

#一次抓五個
import requests
import json
import os
import time
from datetime import datetime
from tqdm import tqdm
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Jina API密鑰
JINA_API_KEY = "jina_2752307cab7a46e29d16c3fcbcdca7e2VPAObQDS2ER66cFvwpmGVIeIN8TG"

# 設置輸出目錄
OUTPUT_DIR = "fraud_data/jina_processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 需要爬取的URL列表
urls_to_crawl = [
    "https://165.npa.gov.tw/#/",
    "https://165.npa.gov.tw/#/articles/C",
    "https://165.npa.gov.tw/#/articles/1",
    "https://165.npa.gov.tw/#/articles/A",
    "https://165.npa.gov.tw/#/articles/6"
]

def crawl_with_jina(url):
    """使用Jina API爬取網頁內容"""
    try:
        # 設置請求頭
        headers = {
            'Authorization': f'Bearer {JINA_API_KEY}',
            'Accept': 'application/json'
        }
        
        # 構建完整URL
        jina_url = f'https://r.jina.ai/{url}'
        
        # 發送請求
        print(f"正在爬取: {url}")
        response = requests.get(jina_url, headers=headers, timeout=30)
        
        # 檢查回應狀態
        if response.status_code != 200:
            print(f"錯誤: Jina API返回狀態碼 {response.status_code}")
            return {
                "url": url,
                "jina_url": jina_url,
                "success": False,
                "error": f"Jina API返回錯誤代碼: {response.status_code}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 獲取內容
        content = response.text
        print(f"成功獲取內容，長度: {len(content)} 字符")
        
        # 解析內容（可選）
        try:
            soup = BeautifulSoup(content, 'html.parser')
            title = soup.title.string if soup.title else "No title"
            print(f"頁面標題: {title}")
        except Exception as e:
            print(f"解析HTML失敗: {e}")
            title = "解析失敗"
        
        # 組織結果
        result = {
            "url": url,
            "jina_url": jina_url,
            "success": True,
            "title": title,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    except Exception as e:
        print(f"爬取過程中出錯: {e}")
        return {
            "url": url,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def save_result(result):
    """將結果保存為JSON文件"""
    try:
        # 從URL生成文件名
        parsed_url = urlparse(result["url"])
        domain = parsed_url.netloc
        path = parsed_url.path.replace("/", "_")
        if path == "":
            path = "_root"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"{domain}{path}_{timestamp}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # 保存JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"已保存結果到: {filepath}")
        return filepath
    
    except Exception as e:
        print(f"保存結果時出錯: {e}")
        return None

def main():
    """主函數"""
    print(f"開始爬取 {len(urls_to_crawl)} 個URL...")
    
    # 創建進度條
    with tqdm(total=len(urls_to_crawl)) as pbar:
        for i, url in enumerate(urls_to_crawl):
            # 顯示進度
            pbar.set_description(f"處理 {url}")
            pbar.update(0)  # 更新進度條描述
            
            # 爬取內容
            result = crawl_with_jina(url)
            
            # 保存結果
            if result:
                save_result(result)
            
            # 更新進度
            pbar.update(1)
            pbar.set_postfix({"完成": f"{i+1}/{len(urls_to_crawl)}", "成功": result["success"]})
            
            # 暫停一下，避免頻繁請求
            if i < len(urls_to_crawl) - 1:  # 最後一個URL不需要等待
                print("等待1秒後繼續下一個URL...")
                time.sleep(1)
    
    print(f"\n爬取完成! 總共處理了 {len(urls_to_crawl)} 個URL")
    print(f"結果保存在: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    # 開始執行
    print("開始執行Jina API網站爬蟲...")
    main()