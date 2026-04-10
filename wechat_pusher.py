#!/usr/bin/env python3
"""
虾米股票系统 - 微信推送模块
通过OpenClaw消息接口推送报告

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research/')

from datetime import datetime
from typing import Dict, List, Optional
import json


class WeChatPusher:
    """微信推送器"""
    
    def __init__(self):
        self.enabled = True
        self.channel = 'openclaw-weixin'  # 微信频道
    
    def build_daily_report(self, picks: List[Dict], market: Dict) -> str:
        """构建每日选股报告"""
        
        # 头部
        report = f"""
🔥 虾米每日选股报告
{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*50}

📊 市场概况
  上证: {market.get('sh000001', {}).get('pct', 0):+.2f}%
  深证: {market.get('sz399001', {}).get('pct', 0):+.2f}%
  创业板: {market.get('sz399006', {}).get('pct', 0):+.2f}%
  成交额: {market.get('total_amount', 'N/A')}
"""
        
        # 热门板块
        if market.get('hot_sectors'):
            report += f"""
🔥 热门板块
"""
            for sector in market['hot_sectors'][:5]:
                report += f"  {sector['name']} {sector['pct']:+.2f}%\n"
        
        # 推荐股票
        if picks:
            strong = [p for p in picks if p.get('recommendation') == '强烈推荐']
            cautious = [p for p in picks if p.get('recommendation') == '谨慎推荐']
            
            if strong:
                report += f"""
🟢 强烈推荐 ({len(strong)}只)
"""
                for stock in strong:
                    report += f"""
📈 {stock['name']}({stock['code']})
   现价: {stock['price']:.2f}元 ({stock['pct']:+.2f}%)
   评分: {stock['score']}/100
   🎯 买入点: {stock.get('buy_point', stock['price']):.2f}元
   🛡️ 止损位: {stock.get('stop_loss', stock['price']*0.92):.2f}元
   📈 目标位: {stock.get('target', stock['price']*1.08):.2f}元
   📝 理由: {stock.get('reason', '技术面良好')}
"""
            
            if cautious:
                report += f"""
🟡 谨慎推荐 ({len(cautious)}只)
"""
                for stock in cautious:
                    report += f"""
⚠️ {stock['name']}({stock['code']})
   现价: {stock['price']:.2f}元 ({stock['pct']:+.2f}%)
   评分: {stock['score']}/100
   建议: {stock.get('suggestion', '观望')}
"""
        
        # 操作建议
        report += f"""
{'='*50}
💡 操作建议
  • 强烈推荐的股票可建仓50%
  • 谨慎推荐的股票30%仓位
  • 严格执行止损纪律
  • 控制在5只以内
{'='*50}
"""
        
        return report
    
    def build_stock_analysis_report(self, stock: Dict) -> str:
        """构建单股分析报告"""
        
        realtime = stock.get('realtime', {})
        chief = stock.get('chief', {})
        arbitration = stock.get('arbitration', {})
        committee_results = stock.get('committee_results', [])
        
        code = stock.get('code', '')
        name = stock.get('name', code)
        price = realtime.get('price', 0)
        pct = realtime.get('pct', 0)
        
        report = f"""
🏛️ 虾米股票分析报告
{name}({code})
{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*50}

💰 当前行情
  现价: {price:.2f}元 ({pct:+.2f}%)
  最高: {realtime.get('high', 0):.2f}元
  最低: {realtime.get('low', 0):.2f}元
"""
        
        # 四委员会裁决
        if committee_results:
            report += f"""
🏛️ 四委员会裁决
"""
            for result in committee_results:
                emoji = "🟢" if "买入" in result.get('action', '') else \
                        "🟡" if "观望" in result.get('action', '') else "🔴"
                report += f"  {emoji} {result['committee']}: {result['avg_score']:.1f}分\n"
                report += f"     {result['conclusion']}\n"
        
        # 综合评分
        if arbitration:
            votes = arbitration.get('votes', {})
            report += f"""
⚖️ 裁决结果
  买入: {votes.get('买入', 0):.0%} | 观望: {votes.get('观望', 0):.0%} | 回避: {votes.get('回避', 0):.0%}
  综合评分: {arbitration.get('final_score', 0):.1f}/100
"""
        
        # 最终决策
        if chief:
            report += f"""
╔════════════════════════════════════╗
║  🏛️ {chief.get('decision', '分析中'):<30}  ║
╠════════════════════════════════════╣
║  💡 {chief.get('action', ''):<30}  ║
╠════════════════════════════════════╣
║  📋 买入: {chief.get('buy_point', 0):.2f}元                ║
║  🛡️ 止损: {chief.get('stop_loss', 0):.2f}元                ║
║  🎯 目标: {chief.get('target', 0):.2f}元                ║
╚════════════════════════════════════╝
"""
        
        return report
    
    def build_portfolio_alert(self, alerts: List[Dict]) -> str:
        """构建持仓提醒"""
        
        if not alerts:
            return ""
        
        report = f"""
⚠️ 持仓风险提醒
{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*50}
"""
        
        for alert in alerts:
            report += f"\n{alert.get('message', '')}\n"
        
        return report
    
    def build_backtest_report(self, results: Dict) -> str:
        """构建回测报告"""
        
        report = f"""
📊 策略回测报告
{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*50}
股票: {results.get('code', 'N/A')}
周期: {results.get('period', 'N/A')}
初始资金: {results.get('initial_capital', 0):,.2f}
"""
        
        for strategy_name, r in results.items():
            if strategy_name in ['code', 'period', 'initial_capital']:
                continue
            
            report += f"""
--- {r.get('strategy', strategy_name)} ---
  总交易: {r.get('total_trades', 0)}
  胜率: {r.get('win_rate', 0):.1f}%
  盈亏比: {r.get('profit_factor', 0):.2f}
  收益率: {r.get('total_return', 0):.2f}%
"""
        
        return report


# 全局实例
wechat_pusher = WeChatPusher()


if __name__ == "__main__":
    # 测试
    print("测试微信推送模块...")
    
    # 测试每日报告
    test_picks = [
        {
            'code': '000977',
            'name': '浪潮信息',
            'price': 67.86,
            'pct': 4.29,
            'score': 78,
            'recommendation': '强烈推荐',
            'buy_point': 65.0,
            'stop_loss': 60.0,
            'target': 75.0,
            'reason': 'AI热点，MACD金叉'
        }
    ]
    
    test_market = {
        'sh000001': {'pct': 1.25},
        'sz399001': {'pct': 1.18},
        'sz399006': {'pct': 0.83},
        'hot_sectors': [
            {'name': 'AI人工智能', 'pct': 5.2},
            {'name': '军工', 'pct': 3.1},
            {'name': '半导体', 'pct': 2.8},
        ]
    }
    
    report = wechat_pusher.build_daily_report(test_picks, test_market)
    print(report)
