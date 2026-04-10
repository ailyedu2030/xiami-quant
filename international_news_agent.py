#!/usr/bin/env python3
"""
虾米量化系统 - 国际新闻事件Agent v1.0
International News Event Agent

监控国际事件对A股的影响:
- 地缘政治 → 军工、黄金、石油
- 科技战 → 半导体、芯片
- 美联储政策 → 金融、出口
- 全球疫情 → 医药、航运
- 气候事件 → 新能源、农业

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# ==================== 新闻源配置 ====================

NEWS_SOURCES = {
    # 英文媒体
    "reuters": {
        "name": "Reuters",
        "url": "https://www.reuters.com",
        "sections": ["world", "business", "technology", "markets"],
        "lang": "en"
    },
    "bbc": {
        "name": "BBC News",
        "url": "https://www.bbc.com/news",
        "sections": ["world", "technology", "business"],
        "lang": "en"
    },
    "ft": {
        "name": "Financial Times",
        "url": "https://www.ft.com",
        "sections": ["world", "markets", "technology"],
        "lang": "en"
    },
    
    # 中文媒体
    "ftchinese": {
        "name": "FT中文网",
        "url": "https://www.ftchinese.com",
        "sections": ["/latest", "/markets", "/china"],
        "lang": "zh"
    },
    "sina": {
        "name": "新浪国际",
        "url": "https://finance.sina.com.cn/world/",
        "sections": [],
        "lang": "zh"
    },
}

# ==================== 事件映射 ====================

EVENT_IMPACT_MAP = {
    # 地缘政治
    "战争": {"sectors": ["军工", "石油", "黄金"], "direction": "positive"},
    "冲突": {"sectors": ["军工", "黄金"], "direction": "positive"},
    "制裁": {"sectors": ["科技", "出口"], "direction": "negative"},
    "峰会": {"sectors": ["金融", "外贸"], "direction": "neutral"},
    
    # 科技
    "AI": {"sectors": ["AI", "半导体", "软件"], "direction": "positive"},
    "芯片": {"sectors": ["半导体", "芯片"], "direction": "positive"},
    "禁令": {"sectors": ["科技", "半导体"], "direction": "negative"},
    "突破": {"sectors": ["科技", "医药"], "direction": "positive"},
    
    # 金融
    "加息": {"sectors": ["银行", "金融"], "direction": "positive"},
    "降息": {"sectors": ["消费", "地产"], "direction": "positive"},
    "QE": {"sectors": ["黄金", "大宗商品"], "direction": "positive"},
    "缩表": {"sectors": ["银行", "股市"], "direction": "negative"},
    
    # 宏观
    "通胀": {"sectors": ["黄金", "商品"], "direction": "positive"},
    "衰退": {"sectors": ["防御股", "黄金"], "direction": "neutral"},
    "疫情": {"sectors": ["医药", "在线"], "direction": "positive"},
    "气候": {"sectors": ["新能源", "农业"], "direction": "positive"},
    
    # 中国相关
    "中美": {"sectors": ["科技", "出口", "半导体"], "direction": "negative"},
    "关税": {"sectors": ["出口", "科技"], "direction": "negative"},
    "合作": {"sectors": ["新能源", "外贸"], "direction": "positive"},
    "峰会": {"sectors": ["金融", "外贸"], "direction": "positive"},
}

# ==================== 新闻Agent类 ====================

class InternationalNewsAgent:
    """
    国际新闻事件Agent
    监控全球事件，分析对A股的影响
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_reuters_news(self, section: str = "world", limit: int = 10) -> List[Dict]:
        """获取Reuters新闻"""
        news_list = []
        try:
            url = f"https://www.reuters.com/news/{section}"
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 查找新闻条目
            articles = soup.find_all('article', class_='story')[:limit]
            
            for article in articles:
                title = article.find('h3')
                if title:
                    news_list.append({
                        'title': title.get_text().strip(),
                        'source': 'Reuters',
                        'section': section,
                        'url': url,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
        except Exception as e:
            print(f"Reuters获取失败: {e}")
        
        return news_list
    
    def get_bbc_news(self, section: str = "world", limit: int = 10) -> List[Dict]:
        """获取BBC新闻"""
        news_list = []
        try:
            url = f"https://www.bbc.com/news/{section}"
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            articles = soup.find_all('div', class_='branded-link')[:limit]
            
            for article in articles:
                news_list.append({
                    'title': article.get_text().strip(),
                    'source': 'BBC',
                    'section': section,
                    'url': url,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                })
        except Exception as e:
            print(f"BBC获取失败: {e}")
        
        return news_list
    
    def get_ftchinese_news(self, limit: int = 10) -> List[Dict]:
        """获取FT中文网新闻"""
        news_list = []
        try:
            url = "https://www.ftchinese.com/"
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            articles = soup.find_all('a', class_='title-link')[:limit]
            
            for article in articles:
                title = article.get_text().strip()
                if title and len(title) > 10:
                    news_list.append({
                        'title': title,
                        'source': 'FT中文网',
                        'section': '财经',
                        'url': url,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
        except Exception as e:
            print(f"FT中文网获取失败: {e}")
        
        return news_list
    
    def analyze_event_impact(self, title: str) -> Dict:
        """
        分析事件对A股的影响
        """
        title_lower = title.lower()
        matched_events = []
        affected_sectors = []
        
        for keyword, impact in EVENT_IMPACT_MAP.items():
            if keyword in title or keyword.lower() in title_lower:
                matched_events.append(keyword)
                sector_list = impact['sectors']
                for sector in sector_list:
                    if sector not in affected_sectors:
                        affected_sectors.append({
                            'sector': sector,
                            'direction': impact['direction']
                        })
        
        if affected_sectors:
            return {
                'has_impact': True,
                'matched_events': matched_events,
                'affected_sectors': affected_sectors,
                'overall_direction': self._calculate_direction(affected_sectors)
            }
        
        return {
            'has_impact': False,
            'matched_events': [],
            'affected_sectors': [],
            'overall_direction': 'neutral'
        }
    
    def _calculate_direction(self, sectors: List[Dict]) -> str:
        """计算整体方向"""
        positive = sum(1 for s in sectors if s['direction'] == 'positive')
        negative = sum(1 for s in sectors if s['direction'] == 'negative')
        
        if positive > negative:
            return 'positive'
        elif negative > positive:
            return 'negative'
        return 'neutral'
    
    def scan_all_sources(self) -> Dict:
        """
        扫描所有新闻源
        """
        all_news = []
        
        # 尝试获取各来源
        sources = [
            ("Reuters", lambda: self.get_reuters_news("world", 10)),
            ("BBC", lambda: self.get_bbc_news("world", 10)),
            ("FT中文网", lambda: self.get_ftchinese_news(10)),
        ]
        
        for name, func in sources:
            try:
                news = func()
                all_news.extend(news)
                print(f"  {name}: {len(news)} 条")
            except Exception as e:
                print(f"  {name}: 失败 - {str(e)[:30]}")
        
        # 分析影响
        events_with_impact = []
        for news in all_news:
            impact = self.analyze_event_impact(news['title'])
            news['impact'] = impact
            if impact['has_impact']:
                events_with_impact.append(news)
        
        return {
            'total_news': len(all_news),
            'events_with_impact': events_with_impact,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("国际新闻事件Agent - 扫描全球事件对A股的影响")
    print("="*80)
    
    agent = InternationalNewsAgent()
    
    print("\n[1] 扫描国际新闻...")
    result = agent.scan_all_sources()
    
    print(f"\n  总新闻数: {result['total_news']}")
    print(f"  影响A股的事件: {len(result['events_with_impact'])}")
    
    if result['events_with_impact']:
        print("\n[2] 影响A股的国际事件:")
        print("-" * 60)
        
        for news in result['events_with_impact'][:10]:
            impact = news['impact']
            direction_emoji = "🟢" if impact['overall_direction'] == 'positive' else \
                            ("🔴" if impact['overall_direction'] == 'negative' else "🟡")
            
            sectors = [s['sector'] for s in impact['affected_sectors']]
            
            print(f"\n{direction_emoji} {news['source']}")
            print(f"   标题: {news['title'][:50]}...")
            print(f"   匹配事件: {', '.join(impact['matched_events'])}")
            print(f"   影响板块: {', '.join(sectors)}")
    
    # 保存结果
    output_file = 'international_news_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[3] 结果已保存: {output_file}")
    print("="*80)

if __name__ == "__main__":
    main()
