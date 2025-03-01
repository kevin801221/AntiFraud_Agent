#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module: utils.py
Description: 提供日誌記錄等共用工具函式。
"""

from datetime import datetime

def log(message: str, level: str = "INFO"):
    """
    簡單的日誌記錄函式，會印出帶有時間戳的訊息。

    Args:
        message (str): 要記錄的訊息。
        level (str): 訊息等級（預設為 "INFO"）。
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")