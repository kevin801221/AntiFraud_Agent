#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module: 1_jina_crawler.py
Description: 定義 JinaCrawler 類別，利用 Jina API 爬取網頁內容。
"""

import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
from core.utils import log

class JinaCrawler:
    """
    使用 Jina API 進行網頁爬取的類別。

    Attributes:
        api_key (str): Jina API 的金鑰。
        requests_made (int): 已發出請求的計數器。
        last_request_time (float): 上一次請求的時間。
        delay (float): 每次請求間的延遲時間（秒）。
    """
    def __init__(self, api_key: str, delay: float = 2):
        self.api_key = api_key
        self.requests_made = 0
        self.last_request_time = 0
        self.delay = delay

    def _rate_limit(self):
        """
        確保每次 API 請求間隔至少 self.delay 秒，以符合速率限制。
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def crawl_url(self, url: str) -> dict:
        """
        爬取單一 URL 的內容，並回傳爬取結果。

        Args:
            url (str): 要爬取的目標網址。

        Returns:
            dict: 包含爬取結果與狀態的字典。
        """
        self._rate_limit()
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        jina_url = f'https://r.jina.ai/{url}'
        log(f"Crawling: {url}")
        try:
            response = requests.get(jina_url, headers=headers, timeout=30)
            self.requests_made += 1
            if response.status_code != 200:
                log(f"Error: Jina API returned status code {response.status_code}", "ERROR")
                return {
                    "url": url,
                    "jina_url": jina_url,
                    "success": False,
                    "error": f"Jina API returned status code: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
            content = response.text
            log(f"Successfully retrieved content, length: {len(content)} characters")
            # 利用 BeautifulSoup 解析 HTML 以取得網頁標題
            try:
                soup = BeautifulSoup(content, 'html.parser')
                title = soup.title.string if soup.title else "No title"
                log(f"Page title: {title}")
            except Exception as e:
                log(f"Failed to parse HTML: {e}", "WARNING")
                title = "Parse failure"
            return {
                "url": url,
                "jina_url": jina_url,
                "success": True,
                "title": title,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            log(f"Error during crawling: {e}", "ERROR")
            return {
                "url": url,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def crawl_urls(self, urls: list) -> dict:
        """
        爬取多個 URL，並回傳整體結果。

        Args:
            urls (list): URL 字串列表。

        Returns:
            dict: 包含所有爬取結果與統計資訊的字典。
        """
        results = []
        log(f"Starting to crawl {len(urls)} URLs...")
        for url in tqdm(urls, desc="Crawling URLs"):
            result = self.crawl_url(url)
            results.append(result)
        combined_results = {
            "total_urls": len(urls),
            "successful_crawls": sum(1 for r in results if r.get("success")),
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        log(f"Crawling completed! Success: {combined_results['successful_crawls']}/{combined_results['total_urls']}")
        return combined_results