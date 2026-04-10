#!/usr/bin/env python3
"""
虾米量化系统 - 新闻事件Agent v2.0
News Event Agent (使用akshare)

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import akshare as ak
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ==================== 新闻Agent ====================

class NewsAgent:
    """新闻事件Agent"""
    
    def __init__(self):
        self.session_start = datetime.now()
    
    def get_market_news(self, hours: int = 24) -> List[Dict]:
        """
        获取市场新闻
        """
        news_list = []
        
        try:
            df = ak.stock_news_em(symbol="A股")
            for _, row in df.iterrows():
                news_list.append({
                    'title': str(row.get('新闻标题', '')),
                    'content': str(row.get('新闻内容', ''))[:200],
                    'time': str(row.get('发布时间', '')),
                    'source': '东方财富',
                    'url': str(row.get('新闻链接', '')),
                })
        except Exception as e:
            print(f"获取市场新闻失败: {e}")
        
        return news_list
    
    def search_stock_news(self, stock_name: str) -> List[Dict]:
        """
        搜索特定股票的新闻
        """
        news_list = []
        
        try:
            # 使用百度搜索股市新闻
            df = ak.stock_news_em(symbol=stock_name)
            for _, row in df.iterrows():
                news_list.append({
                    'title': str(row.get('新闻标题', '')),
                    'content': str(row.get('新闻内容', ''))[:200],
                    'time': str(row.get('发布时间', '')),
                    'source': '东方财富',
                })
        except Exception as e:
            print(f"搜索{stock_name}新闻失败: {e}")
        
        return news_list
    
    def analyze_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        分析新闻情绪
        """
        if not news_list:
            return {
                'sentiment': 'neutral',
                'score': 50,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'hot_topics': []
            }
        
        positive_keywords = [
            '利好', '涨', '突破', '增长', '盈利', '创新高', '增持',
            '买入', '推荐', '超预期', '景气', '回暖', '政策支持',
            '国产替代', '订单爆发', '业绩大幅', '净利润增长',
            '签约', '中标', '合作', '订单', '扩产', '量产'
        ]
        
        negative_keywords = [
            '利空', '跌', '减持', '亏损', '风险', '警示', '问询',
            '造假', '处罚', '立案', '调查', '业绩下滑', '不及预期',
            '商誉减值', '库存积压', '竞争加剧', '出口受限', '大跌',
            '闪崩', '破发', 'st', '*st', '退市'
        ]
        
        hot_keywords = [
            '降准', '降息', '加息', '缩表', '通胀', '原油',
            '半导体', '芯片', '新能源', '锂电', '医药', '茅台',
            '宁德', '中美', '贸易战', '制裁', '出口管制',
            '人工智能', 'AI', '机器人', '固态电池'
        ]
        
        scores = []
        pos_count = 0
        neg_count = 0
        neu_count = 0
        hot_topics = []
        
        for news in news_list:
            text = news.get('title', '') + news.get('content', '')
            
            pos_found = sum(1 for k in positive_keywords if k in text)
            neg_found = sum(1 for k in negative_keywords if k in text)
            
            if pos_found > neg_found:
                scores.append(70 + min(pos_found * 5, 20))
                pos_count += 1
            elif neg_found > pos_found:
                scores.append(30 - min(neg_found * 5, 20))
                neg_count += 1
            else:
                scores.append(50)
                neu_count += 1
            
            # 检测热点话题
            for k in hot_keywords:
                if k in text and k not in hot_topics:
                    hot_topics.append(k)
        
        avg_score = sum(scores) / len(scores) if scores else 50
        
        if avg_score >= 60:
            sentiment = 'positive'
        elif avg_score <= 40:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': round(avg_score, 1),
            'positive_count': pos_count,
            'negative_count': neg_count,
            'neutral_count': neu_count,
            'hot_topics': hot_topics[:5],
            'news_count': len(news_list)
        }
    
    def analyze_for_stock(self, stock_name: str, stock_code: str = '') -> Dict:
        """
        分析特定股票的新闻情绪
        """
        news = self.search_stock_news(stock_name)
        sentiment = self.analyze_sentiment(news)
        
        return {
            'stock': stock_name,
            'code': stock_code,
            'news': news[:5],
            'sentiment': sentiment,
            'recommendation': self._sentiment_to_recommendation(sentiment)
        }
    
    def _sentiment_to_recommendation(self, sentiment: Dict) -> str:
        """根据情绪给出建议"""
        score = sentiment['score']
        count = sentiment['news_count']
        
        if count == 0:
            return '无新闻，保持观察'
        
        if score >= 65:
            return '积极信号，可关注'
        elif score >= 55:
            return '略偏乐观，谨慎跟进'
        elif score >= 45:
            return '中性，等待明确信号'
        elif score >= 35:
            return '略偏谨慎，注意风险'
        else:
            return '回避，等待利空释放'
    
    def get_macro_news(self) -> List[Dict]:
        """
        获取宏观新闻
        """
        macro_news = []
        
        # 获取A股新闻然后过滤宏观相关
        all_news = self.get_market_news(hours=48)
        
        macro_keywords = [
            '央行', '降准', '降息', '加息', '美联储', '鲍威尔',
            '财政部', '证监会', '银保监会', 'CPI', 'PPI', 'GDP',
            '进出口', '外贸', '汇率', '人民币', '美元', '美股',
            '欧股', '日经', '期货', '原油', '黄金', '大宗商品'
        ]
        
        for news in all_news:
            text = news.get('title', '') + news.get('content', '')
            if any(k in text for k in macro_keywords):
                macro_news.append(news)
        
        return macro_news[:20]

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("虾米量化系统 - 新闻事件Agent v2.0")
    print("="*80)
    
    agent = NewsAgent()
    
    # 1. 获取市场新闻
    print("\n[1] 获取市场新闻...")
    market_news = agent.get_market_news(hours=24)
    print(f"    获取到 {len(market_news)} 条新闻")
    
    # 2. 分析市场情绪
    print("\n[2] 市场情绪分析...")
    sentiment = agent.analyze_sentiment(market_news)
    
    emoji = "🟢" if sentiment['sentiment'] == 'positive' else ("🔴" if sentiment['sentiment'] == 'negative' else "🟡")
    print(f"    {emoji} 情绪: {sentiment['sentiment']}")
    print(f"    评分: {sentiment['score']}")
    print(f"    正面: {sentiment['positive_count']} | 负面: {sentiment['negative_count']} | 中性: {sentiment['neutral_count']}")
    if sentiment['hot_topics']:
        print(f"    热点: {' '.join(sentiment['hot_topics'])}")
    
    # 3. 显示最新新闻
    print("\n[3] 最新新闻...")
    for i, news in enumerate(market_news[:5]):
        title = news.get('title', '')[:50]
        print(f"    {i+1}. {title}...")
        print(f"       [{news.get('source', '')}] {news.get('time', '')}")
    
    # 4. 重点股票新闻
    print("\n[4] 重点股票新闻...")
    key_stocks = [
        ('北方华创', 'sz.002371'),
        ('贵州茅台', 'sh.600519'),
        ('宁德时代', 'sz.300750'),
        ('比亚迪', 'sz.002594'),
        ('浪潮信息', 'sz.000977'),
    ]
    
    results = []
    for name, code in key_stocks:
        try:
            result = agent.analyze_for_stock(name, code)
            results.append(result)
            
            se = result['sentiment']
            emoji = "🟢" if se['sentiment'] == 'positive' else ("🔴" if se['sentiment'] == 'negative' else "🟡")
            print(f"\n    {emoji} {name}({code})")
            print(f"       情绪: {se['sentiment']} | 评分: {se['score']} | 新闻数: {se['news_count']}")
            print(f"       建议: {result['recommendation']}")
        except Exception as e:
            print(f"    ❌ {name}: {e}")
    
    # 5. 宏观新闻
    print("\n[5] 宏观新闻...")
    macro_news = agent.get_macro_news()
    print(f"    获取到 {len(macro_news)} 条宏观新闻")
    for i, news in enumerate(macro_news[:3]):
        print(f"    {i+1}. {news.get('title', '')[:40]}...")
    
    # 6. 保存结果
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'market_sentiment': sentiment,
        'stock_sentiments': [
            {
                'name': r['stock'],
                'code': r['code'],
                'sentiment': r['sentiment'],
                'recommendation': r['recommendation']
            } for r in results
        ],
        'macro_news_count': len(macro_news)
    }
    
    with open('news_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*80)
    print("✅ 新闻分析完成")
    print("="*80)

if __name__ == "__main__":
    main()
