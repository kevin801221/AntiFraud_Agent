#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module: 2_content_processor.py
Description: 定義 ContentProcessor 類別，用於處理與整理爬取內容，並選用 OpenAI API 生成結構化資料。
"""

import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
from core.utils import log

class ContentProcessor:
    """
    處理爬取內容並利用 OpenAI API 生成結構化資料。

    Attributes:
        api_key (str): OpenAI API 金鑰。
        requests_made (int): 已發出 API 請求的計數。
        last_request_time (float): 上一次 API 請求的時間。
        delay (float): API 請求間的延遲秒數。
    """
    def __init__(self, api_key: str = None, delay: float = 1):
        self.api_key = api_key
        self.requests_made = 0
        self.last_request_time = 0
        self.delay = delay

    def _rate_limit(self):
        """
        控制 API 請求的速率，避免過於頻繁的呼叫。
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def _parse_content(self, content: str) -> str:
        """
        嘗試將原始內容解析為 JSON 格式，若失敗則使用 BeautifulSoup 解析 HTML 提取文字。

        Args:
            content (str): 原始爬取內容。

        Returns:
            str: 解析後的純文字內容。
        """
        try:
            content_json = json.loads(content)
            if "data" in content_json and "content" in content_json["data"]:
                return content_json["data"]["content"]
            else:
                log("Warning: Could not find content in JSON structure", "WARNING")
                return content
        except json.JSONDecodeError:
            # 若非 JSON 格式，則使用 BeautifulSoup 提取文字
            try:
                soup = BeautifulSoup(content, 'html.parser')
                paragraphs = soup.find_all('p')
                if paragraphs:
                    return "\n\n".join([p.get_text() for p in paragraphs])
                body = soup.body
                if body:
                    return body.get_text(separator="\n\n")
                return soup.get_text(separator="\n\n")
            except Exception:
                return content

    def _process_with_openai(self, content: str, url: str) -> dict:
        """
        呼叫 OpenAI API，根據指定 prompt 生成結構化資料。

        Args:
            content (str): 要處理的內容。
            url (str): 來源網頁的 URL。

        Returns:
            dict: 包含 OpenAI 處理結果的字典。
        """
        if not self.api_key:
            return {"success": False, "error": "No OpenAI API key provided"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        prompt = f"""
            以下是從「165全民防騙網」({url})使用Jina API擷取的內容。
            請將此內容整理為結構化資料，包含以下資訊：
            
            1. 網站主題摘要
            2. 主要的詐騙警示訊息
            3. 列出至少3種詐騙類型
            4. 提取預防詐騙的建議
            5. 提取的重要連結與資源
            
            請以JSON格式回應，確保所有內容都是繁體中文。
            
            網頁內容：
            {content[:4000]}  # 限制內容長度以避免超出 token 上限
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
        try:
            self._rate_limit()
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            self.requests_made += 1
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    structured_content = json.loads(result["choices"][0]["message"]["content"])
                    return {"success": True, "structured_data": structured_content}
                else:
                    return {"success": False, "error": "OpenAI response missing content", "raw_response": str(result)}
            else:
                return {"success": False, "error": f"OpenAI API returned error code: {response.status_code}", "raw_response": response.text}
        except Exception as e:
            return {"success": False, "error": f"Error processing with OpenAI: {str(e)}"}

    def process_content(self, crawl_result: dict) -> dict:
        """
        處理單筆爬取結果：若爬取成功則解析內容並呼叫 OpenAI API 進行整理，否則跳過處理。

        Args:
            crawl_result (dict): 單筆爬取結果資料。

        Returns:
            dict: 包含處理後結果的字典。
        """
        if not crawl_result.get("success", False):
            log(f"Skipping processing for failed crawl: {crawl_result.get('url', 'unknown')}", "WARNING")
            return {
                "url": crawl_result.get("url", "unknown"),
                "success": False,
                "error": "Skipped processing due to failed crawl",
                "original_error": crawl_result.get("error", "Unknown error"),
                "timestamp": datetime.now().isoformat()
            }
        content = crawl_result.get("content", "")
        parsed_content = self._parse_content(content)
        processed_data = {}
        if self.api_key:
            log(f"Processing content with OpenAI for: {crawl_result.get('url', 'unknown')}")
            openai_result = self._process_with_openai(parsed_content, crawl_result.get("url", ""))
            processed_data = {
                "url": crawl_result.get("url", ""),
                "success": True,
                "title": crawl_result.get("title", ""),
                "jina_raw_response_sample": content[:500] + "..." if len(content) > 500 else content,
                "parsed_content_sample": parsed_content[:1000] + "..." if len(parsed_content) > 1000 else parsed_content,
                "openai_processing": openai_result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            log("Warning: No OpenAI API key provided. Returning parsed content only.", "WARNING")
            processed_data = {
                "url": crawl_result.get("url", ""),
                "success": True,
                "title": crawl_result.get("title", ""),
                "parsed_content": parsed_content,
                "timestamp": datetime.now().isoformat()
            }
        return processed_data

    def process_crawl_results(self, crawl_results: dict) -> dict:
        """
        處理多筆爬取結果，並彙整每筆結果的處理狀態與內容。

        Args:
            crawl_results (dict): 包含多筆爬取結果的字典。

        Returns:
            dict: 整合後的處理結果資料。
        """
        results = []
        individual_results = crawl_results.get("results", [])
        log(f"Starting to process {len(individual_results)} crawl results...")
        for result in tqdm(individual_results, desc="Processing crawl results"):
            processed_result = self.process_content(result)
            results.append(processed_result)
        combined_results = {
            "total_items": len(individual_results),
            "successful_processes": sum(1 for r in results if r.get("success")),
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        log(f"Processing completed! Success: {combined_results['successful_processes']}/{combined_results['total_items']}")
        return combined_results