#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
Description: Fraud Data Pipeline 的入口程式。
依序執行：
  1. 使用 JinaCrawler 爬取網頁內容。
  2. 使用 ContentProcessor 處理爬取內容。
  3. 使用 TrainingDataGenerator 生成訓練資料。
"""

import os
import sys
import json
from datetime import datetime
from core.jina_crawler import JinaCrawler
from core.content_processor import ContentProcessor
from core.training_data_generator import TrainingDataGenerator
from core.utils import log

# 配置參數
CONFIG = {
    "JINA_API_KEY": os.getenv("JINA_API_KEY"),  # 從環境變數讀取 Jina API 金鑰
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),  # 從環境變數讀取 OpenAI API 金鑰
    "BASE_DIR": "fraud_data",
    "CRAWL_DIR": "fraud_data/01_crawled_data",
    "PROCESSED_DIR": "fraud_data/02_summarized_data",
    "TRAINING_DIR": "fraud_data/03_training_data",
    "JINA_DELAY": 2,      # Jina API 呼叫間隔秒數
    "OPENAI_DELAY": 1,    # OpenAI API 呼叫間隔秒數
    "BASE_URLS" : [
    # 165 全民防詐騙網首頁與分類（確認有內容的部分）
    "https://165.npa.gov.tw/#/",             # 首頁
    "https://165.npa.gov.tw/#/articles/C",     # 分類總覽（若有內容）
    
    # 您提供的具體文章 URL（確保這些頁面有實質資料）
    "https://165.npa.gov.tw/#/article/C/1641",
    "https://165.npa.gov.tw/#/article/C/1585",
    "https://165.npa.gov.tw/#/article/C/1576",
    "https://165.npa.gov.tw/#/article/C/1551",
    "https://165.npa.gov.tw/#/article/C/1543",
    "https://165.npa.gov.tw/#/article/C/1516",
    "https://165.npa.gov.tw/#/article/C/1477",
    "https://165.npa.gov.tw/#/article/C/1474",
    "https://165.npa.gov.tw/#/article/C/1467",
    "https://165.npa.gov.tw/#/article/C/1466",
    "https://165.npa.gov.tw/#/article/C/1422",
    "https://165.npa.gov.tw/#/article/C/1425",
    
    # 防詐騙報告中提及的其他外部來源（補充多樣性與知識豐富度）
    "https://www.wechat.com/",
    "https://www.taobao.com/",
    "http://www.cnnic.net.cn/",
    "https://www.taiwannews.com.tw/",
    "https://www.scmp.com/",
    "https://www.bbc.com/",
    "https://www.thestar.com.my/",
    "https://focustaiwan.tw/",
    "https://www.statista.com/",
    "https://www.phishing.org/",
    "https://www.ftc.gov/complaint",
    "https://beinternetawesome.withgoogle.com/",
    "https://www.microsoft.com/",
    "https://www.virustotal.com/",
    "https://whois.domaintools.com/",
    "https://cybersecurityventures.com/",
    "https://www.scamwatch.gov.au/",
    "https://www.truecaller.com/",
    "https://www.t-mobile.com/scam-shield",
    "https://www.gartner.com/",
    "https://www.ic3.gov/"
],
    "VERBOSE": True
}

# 確保資料夾存在
for directory in [CONFIG["CRAWL_DIR"], CONFIG["PROCESSED_DIR"], CONFIG["TRAINING_DIR"]]:
    os.makedirs(directory, exist_ok=True)

def run_pipeline(urls=None):
    """
    執行完整的防詐騙資料處理流程：
      1. 爬取指定 URL。
      2. 處理爬取內容。
      3. 生成訓練資料並存檔。

    Args:
        urls (list, optional): 自定義 URL 列表，若未提供則使用 CONFIG["BASE_URLS"]。
    """
    try:
        # 初始化各個模組
        crawler = JinaCrawler(CONFIG["JINA_API_KEY"], delay=CONFIG["JINA_DELAY"])
        processor = ContentProcessor(CONFIG["OPENAI_API_KEY"], delay=CONFIG["OPENAI_DELAY"])
        generator = TrainingDataGenerator()

        urls = urls or CONFIG["BASE_URLS"]

        # Stage 1: 爬取網頁內容
        log("Starting Stage 1: Web Crawling")
        crawl_results = crawler.crawl_urls(urls)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crawl_file = os.path.join(CONFIG["CRAWL_DIR"], f"crawl_results_{timestamp}.json")
        with open(crawl_file, 'w', encoding='utf-8') as f:
            json.dump(crawl_results, f, ensure_ascii=False, indent=2)
        log(f"Crawl results saved to {crawl_file}")

        # Stage 2: 處理爬取內容
        log("Starting Stage 2: Content Processing")
        processed_results = processor.process_crawl_results(crawl_results)
        processed_file = os.path.join(CONFIG["PROCESSED_DIR"], f"processed_results_{timestamp}.json")
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed_results, f, ensure_ascii=False, indent=2)
        log(f"Processed results saved to {processed_file}")

        # Stage 3: 生成訓練資料
        log("Starting Stage 3: Training Data Generation")
        training_data = generator.generate_training_data(processed_results)
        training_file = os.path.join(CONFIG["TRAINING_DIR"], f"training_data_{timestamp}.json")
        with open(training_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        log(f"Training data saved to {training_file}")

        log("Pipeline completed successfully!")
        return training_file
    except Exception as e:
        log(f"Pipeline failed: {str(e)}", "ERROR")
        raise

if __name__ == "__main__":
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
        run_pipeline(urls)
    else:
        run_pipeline()