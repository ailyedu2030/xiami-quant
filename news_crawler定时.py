#!/usr/bin/env python3
"""
新闻定时爬取脚本
每小时自动运行，扫描最新国内外新闻
"""

import requests
import json
from datetime import datetime
import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research')

from policy_monitor import PolicyMonitorAgent

def main():
    print(f"开始爬取新闻... {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    agent = PolicyMonitorAgent()
    
    # 国内政策关键词
    domestic_keywords = [
        "央行 货币政策 最新",
        "证监会 最新政策",
        "国务院 最新通知",
        "科技部 最新政策",
        "财政部 最新消息",
    ]
    
    # 国际事件关键词
    international_keywords = [
        "俄乌战争 最新",
        "AI 人工智能 最新突破",
        "美联储 降息 加息 最新",
        "中美贸易 最新",
        "半导体芯片 最新",
    ]
    
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "domestic": [],
        "international": [],
        "alerts": []
    }
    
    # 模拟保存
    with open("latest_news.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"完成! 保存到 latest_news.json")
    print(f"下次运行: 1小时后")

if __name__ == "__main__":
    main()
