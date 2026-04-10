#!/usr/bin/env python3
"""
实时新闻监控脚本 v2.0
Real-time News Monitor

工作日盘中(9:30-11:30, 13:00-15:00)每30分钟自动运行
通过web_search获取最新新闻，分析对A股的影响

使用方法:
    python3 realtime_news_cron.py

或设置crontab:
    */30 9,10,11,13,14,15 * * 1-5 python3 /path/to/realtime_news_cron.py

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ==================== 配置 ====================

NEWS_KEYWORDS = {
    # 国内政策
    "国内政策": [
        "央行 降准 降息 最新",
        "证监会 最新政策 2026",
        "国务院 重要通知",
        "半导体 国产替代 政策",
        "科技部 最新政策",
    ],
    # 国际事件
    "国际事件": [
        "俄乌战争 最新 2026",
        "AI 人工智能 最新突破",
        "美联储 加息 降息 最新",
        "中美贸易 最新",
        "半导体芯片 最新消息",
    ],
    # 市场热点
    "市场热点": [
        "A股 今日 热点 板块",
        "军工 最新 政策",
        "新能源 最新 政策",
        "医药 最新 政策",
        "白酒 最新 消息",
    ]
}

# 板块影响映射
SECTOR_IMPACT = {
    # 地缘政治
    "战争": ["军工", "石油", "黄金"],
    "冲突": ["军工", "黄金"],
    "制裁": ["科技", "出口"],
    
    # 科技
    "AI": ["AI", "半导体", "软件"],
    "人工智能": ["AI", "半导体", "软件"],
    "芯片": ["半导体", "芯片"],
    "半导体": ["半导体", "芯片"],
    "突破": ["科技", "医药"],
    
    # 金融
    "加息": ["银行", "金融"],
    "降息": ["消费", "地产", "黄金"],
    "宽松": ["银行", "金融", "券商"],
    
    # 大宗商品
    "原油": ["石油", "化工"],
    "黄金": ["黄金", "珠宝"],
    
    # 中国政策
    "央行": ["银行", "金融", "券商"],
    "证监会": ["券商", "金融"],
    "半导体": ["半导体", "芯片", "AI"],
    "新能源": ["新能源", "光伏", "储能"],
    "军工": ["军工", "无人机"],
    "医药": ["医药", "医疗器械"],
    "白酒": ["白酒", "消费"],
    "消费": ["消费", "零售", "食品"],
}

# ==================== 新闻分析类 ====================

class NewsAnalyzer:
    """新闻分析器"""
    
    def __init__(self):
        self.sector_impact = SECTOR_IMPACT
    
    def analyze(self, news_text: str) -> Dict:
        """分析单条新闻"""
        news_lower = news_text.lower()
        matched_keywords = []
        affected_sectors = []
        
        for keyword, sectors in self.sector_impact.items():
            if keyword in news_text or keyword.lower() in news_lower:
                matched_keywords.append(keyword)
                for sector in sectors:
                    if sector not in affected_sectors:
                        affected_sectors.append(sector)
        
        # 判断方向
        negative_keywords = ["制裁", "限制", "打压", "暴跌", "大跌", "利空", "衰退"]
        positive_keywords = ["突破", "增长", "利好", "大涨", "创新高", "超预期"]
        
        direction = "neutral"
        for kw in negative_keywords:
            if kw in news_text:
                direction = "negative"
                break
        for kw in positive_keywords:
            if kw in news_text:
                direction = "positive"
                break
        
        return {
            "has_impact": len(affected_sectors) > 0,
            "keywords": matched_keywords,
            "sectors": affected_sectors,
            "direction": direction,
            "severity": "high" if len(affected_sectors) >= 3 else ("medium" if len(affected_sectors) >= 2 else "low")
        }

# ==================== 存储类 ====================

class NewsStore:
    """新闻存储器"""
    
    def __init__(self, path: str):
        self.path = path
        self.data = self._load()
    
    def _load(self) -> Dict:
        """加载历史数据"""
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"news": [], "alerts": [], "last_update": None}
    
    def _save(self):
        """保存数据"""
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_news(self, news_list: List[Dict]):
        """添加新闻"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for news in news_list:
            if news.get("has_impact"):
                self.data["news"].append({
                    **news,
                    "timestamp": timestamp
                })
        
        # 只保留最近100条
        self.data["news"] = self.data["news"][-100:]
        self.data["last_update"] = timestamp
        self._save()
    
    def add_alert(self, alert: Dict):
        """添加警报"""
        self.data["alerts"].append({
            **alert,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        # 只保留最近50条
        self.data["alerts"] = self.data["alerts"][-50:]
        self._save()
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """获取最近的警报"""
        recent = []
        now = datetime.now()
        
        for alert in self.data.get("alerts", []):
            try:
                alert_time = datetime.strptime(alert["timestamp"], "%Y-%m-%d %H:%M")
                diff = (now - alert_time).total_seconds() / 3600
                if diff <= hours:
                    recent.append(alert)
            except:
                pass
        
        return recent

# ==================== 主程序 ====================

def main():
    print("="*80)
    print(f"实时新闻监控 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*80)
    
    analyzer = NewsAnalyzer()
    store = NewsStore("news_history.json")
    
    # 检查是否有web_search可用
    has_websearch = False
    try:
        from web_search import web_search
        has_websearch = True
        print("✅ web_search 可用")
    except ImportError:
        print("⚠️ web_search 不可用，使用模拟数据")
    
    all_news = []
    breaking_alerts = []
    
    if has_websearch:
        # 使用真实的web_search
        for category, keywords in NEWS_KEYWORDS.items():
            print(f"\n[{category}]")
            for keyword in keywords[:2]:  # 每个类别最多2个关键词
                try:
                    results = web_search(query=keyword, count=3)
                    if results and "results" in results:
                        for item in results["results"]:
                            news_text = item.get("title", "") + " " + item.get("snippet", "")
                            analysis = analyzer.analyze(news_text)
                            
                            news_entry = {
                                "category": category,
                                "keyword": keyword,
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                **analysis
                            }
                            
                            all_news.append(news_entry)
                            
                            if analysis["has_impact"] and analysis["severity"] in ["high", "medium"]:
                                breaking_alerts.append(news_entry)
                            
                            print(f"  ✓ {keyword[:20]}... → {', '.join(analysis['sectors'][:3]) if analysis['sectors'] else '无直接影响'}")
                
                except Exception as e:
                    print(f"  ✗ {keyword}: {str(e)[:30]}")
    else:
        # 模拟新闻数据
        print("\n[模拟模式]")
        sample_news = [
            {"title": "俄乌战争持续影响全球市场", "category": "国际事件", "severity": "high"},
            {"title": "国产AI芯片实现重大突破", "category": "科技", "severity": "high"},
            {"title": "央行宣布降准政策", "category": "国内政策", "severity": "high"},
        ]
        
        for news in sample_news:
            analysis = analyzer.analyze(news["title"])
            all_news.append({**news, **analysis, "keyword": "", "url": ""})
            if analysis["has_impact"]:
                breaking_alerts.append(all_news[-1])
    
    # 保存新闻
    store.add_news(all_news)
    
    # 输出警报
    print("\n" + "="*80)
    print("📰 新闻分析结果")
    print("="*80)
    
    if breaking_alerts:
        print(f"\n🚨 重大发现 ({len(breaking_alerts)} 条):")
        for alert in breaking_alerts[:5]:
            direction_emoji = "🟢" if alert["direction"] == "positive" else ("🔴" if alert["direction"] == "negative" else "🟡")
            sectors = ", ".join(alert["sectors"][:4])
            print(f"\n{direction_emoji} {alert['title'][:40]}...")
            print(f"   影响板块: {sectors}")
            print(f"   方向: {alert['direction']} | 严重度: {alert['severity']}")
        
        # 保存警报
        for alert in breaking_alerts:
            store.add_alert(alert)
    else:
        print("\n✅ 无重大发现，市场平稳")
    
    # 保存最新结果
    output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_news": len(all_news),
        "breaking_alerts": len(breaking_alerts),
        "alerts": breaking_alerts[:5]
    }
    
    with open("breaking_news.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 结果已保存")
    print(f"下次运行: 30分钟后")

if __name__ == "__main__":
    main()
