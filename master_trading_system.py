#!/usr/bin/env python3
"""
虾米专业级股票决策系统 - 完整架构

三层多智能体系统:
1. 战术专家层 (4个): 2560/尾盘/筹码/隔夜
2. 传统专家层 (5个): 技术/基本面/情绪/国际/回测
3. 决策委员会层: 5票投票制

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import baostock as bs

# ==================== 第一层: 战术专家智能体 ====================
from tactic_agents import (
    Agent2560, AgentClosingTime, AgentChips, AgentOvernight,
    TacticAgentFactory, TacticSummary
)


# ==================== 第二层: 技术面专家 ====================
class AgentTechnical:
    """技术面专家智能体"""
    
    def __init__(self):
        self.name = "技术面专家"
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # MA
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma_bullish = ma5 > ma10 > ma20
        
        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd_line = exp12 - exp26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_bullish = macd_line.iloc[-1] > signal_line.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_val = gain / loss
        rsi = (100 - (100 / (1 + rs_val))).iloc[-1]
        
        # KDJ
        period = 9
        low_n = low.rolling(period).min()
        high_n = high.rolling(period).max()
        rsv = (close - low_n) / (high_n - low_n) * 100
        k_series = rsv.ewm(com=2, adjust=False).mean()
        d_series = k_series.ewm(com=2, adjust=False).mean()
        k = k_series.iloc[-1]
        d = d_series.iloc[-1]
        kdj_bullish = k > d
        
        # 布林带
        bb_mid = close.rolling(20).mean().iloc[-1]
        bb_std = close.rolling(20).std().iloc[-1]
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        bb_position = (close.iloc[-1] - bb_lower) / (bb_upper - bb_lower) * 100
        
        # ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = atr / close.iloc[-1] * 100
        
        # 综合评分
        score = 0
        if ma_bullish: score += 25
        if macd_bullish: score += 25
        if 40 <= rsi <= 60: score += 20
        if kdj_bullish: score += 15
        if 20 <= bb_position <= 80: score += 15
        
        return {
            'score': min(100, score),
            'signal': '🟢 买入' if score >= 70 else ('🟡 持有' if score >= 50 else '🔴 观望'),
            'indicators': {
                '均线多头': '✅' if ma_bullish else '❌',
                'MACD': '✅' if macd_bullish else '❌',
                'RSI': f'{rsi:.1f}',
                'KDJ': '✅' if kdj_bullish else '❌',
                '布林位置': f'{bb_position:.1f}%',
                'ATR波动': f'{atr_pct:.2f}%'
            }
        }


# ==================== 第三层: 决策委员会 ====================
class DecisionCommittee:
    """
    决策委员会 - 最终决策机构
    
    5票投票制:
    - 趋势委员: 均线+MACD+K线趋势
    - 价值委员: 基本面+估值
    - 资金委员: 成交量+资金流向
    - 风控委员: 止损位+波动率
    - 时机委员: 战法共振+买入时机
    """
    
    def __init__(self):
        self.name = "决策委员会"
        self.members = [
            "趋势委员", "价值委员", "资金委员", 
            "风控委员", "时机委员"
        ]
    
    def vote(self, technical: Dict, tactic_summary: Dict, 
             stock_name: str, stock_code: str) -> Dict:
        """5票投票"""
        votes = {}
        
        # 趋势委员: 技术面 + 2560战法
        tech_score = technical.get('score', 0)
        tactic_avg = tactic_summary.get('avg_score', 0)
        trend_score = (tech_score + tactic_avg) / 2
        votes['趋势委员'] = {
            'vote': '🟢 买入' if trend_score >= 65 else ('🟡 持有' if trend_score >= 50 else '🔴 回避'),
            'score': trend_score
        }
        
        # 价值委员: 基本面（简化）
        # TODO: 接入基本面专家
        value_score = 60  # 默认中等
        votes['价值委员'] = {
            'vote': '🟡 持有',
            'score': value_score
        }
        
        # 资金委员: 成交量 + 筹码
        chip_score = tactic_summary.get('scores', [50])[2] if len(tactic_summary.get('scores', [])) > 2 else 50
        money_score = (tech_score * 0.5 + chip_score * 0.5)
        votes['资金委员'] = {
            'vote': '🟢 买入' if money_score >= 60 else ('🟡 持有' if money_score >= 45 else '🔴 回避'),
            'score': money_score
        }
        
        # 风控委员: ATR + RSI
        rsi = technical.get('indicators', {}).get('RSI', '50')
        if isinstance(rsi, str):
            rsi_val = float(rsi) if rsi.replace('.', '').isdigit() else 50
        else:
            rsi_val = float(rsi)
        risk_score = 100 - abs(rsi_val - 50) * 2
        votes['风控委员'] = {
            'vote': '🟢 买入' if risk_score >= 60 else ('🟡 持有' if risk_score >= 40 else '🔴 回避'),
            'score': risk_score
        }
        
        # 时机委员: 战法共振
        buy_count = tactic_summary.get('buy_count', 0)
        timing_score = min(100, buy_count * 25 + 30)
        votes['时机委员'] = {
            'vote': '🟢 买入' if timing_score >= 70 else ('🟡 持有' if timing_score >= 50 else '🔴 回避'),
            'score': timing_score
        }
        
        # 汇总投票
        buy_votes = sum(1 for v in votes.values() if '🟢' in v['vote'])
        hold_votes = sum(1 for v in votes.values() if '🟡' in v['vote'])
        sell_votes = sum(1 for v in votes.values() if '🔴' in v['vote'])
        
        # 最终决策
        if buy_votes >= 4:
            final = "🟢 强烈买入"
        elif buy_votes >= 3:
            final = "🟢 建议买入"
        elif hold_votes >= 4:
            final = "🟡 观望"
        elif buy_votes >= 2:
            final = "🟡 谨慎买入"
        elif sell_votes >= 3:
            final = "🔴 建议卖出"
        else:
            final = "⚪ 方向不明"
        
        return {
            'votes': votes,
            'buy_votes': buy_votes,
            'hold_votes': hold_votes,
            'sell_votes': sell_votes,
            'final_decision': final
        }
    
    def print_report(self, vote_result: Dict, technical: Dict, 
                     tactic_summary: Dict, stock_name: str, stock_code: str):
        """打印决策报告"""
        print(f"\n{'='*65}")
        print(f"  🏛️ 虾米决策委员会 - 最终裁决")
        print(f"{'='*65}")
        print(f"  股票: {stock_name}({stock_code})")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*65}")
        
        print(f"\n  📊 各委员投票:")
        print(f"  {'─'*55}")
        for member, data in vote_result['votes'].items():
            emoji = "🟢" if '🟢' in data['vote'] else ("🟡" if '🟡' in data['vote'] else "🔴")
            print(f"  │ {member}: {emoji} {data['vote']:<10} (评分: {data['score']:>5.1f})")
        
        print(f"  {'─'*55}")
        print(f"  │")
        print(f"  │  投票结果: 🟢买入={vote_result['buy_votes']}  🟡持有={vote_result['hold_votes']}  🔴回避={vote_result['sell_votes']}")
        print(f"  │")
        print(f"  ╞═══════════════════════════════════════════════════════════╡")
        print(f"  ║  🏛️ 最终裁决: {vote_result['final_decision']:<25}      ║")
        print(f"  ╚═══════════════════════════════════════════════════════════╝")
        
        print(f"\n  📈 技术面评分: {technical.get('score', 0)}/100")
        print(f"  🎯 战术面评分: {tactic_summary.get('avg_score', 0)}/100")


# ==================== 主分析函数 ====================
def analyze_stock_full(code: str, name: str = "") -> Optional[Dict]:
    """
    完整股票分析 - 三层智能体 + 决策委员会
    
    Args:
        code: 股票代码 (e.g., "600519")
        name: 股票名称
    
    Returns:
        完整分析结果字典
    """
    # 获取数据
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        symbol, 'date,open,high,low,close,volume,pctChg',
        start_date=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        end_date='2026-04-09', frequency='d', adjustflag='2'
    )
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if len(data) < 30:
        print(f"❌ 数据不足: {name}({code})")
        return None
    
    df = pd.DataFrame(data, columns=rs.fields)
    for col in ['open','high','low','close','volume','pctChg']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    
    if not name:
        name = code
    
    # ========== 第一层: 战术专家 ==========
    print(f"\n{'='*65}")
    print(f"  🎯 第一层: 战术专家智能体")
    print(f"{'='*65}")
    
    tactic_results = TacticAgentFactory.run_all(df, name, code)
    TacticSummary.print_tactic_report(tactic_results, name, code)
    tactic_summary = TacticSummary.summarize(tactic_results)
    
    # ========== 第二层: 技术面专家 ==========
    print(f"\n{'='*65}")
    print(f"  📈 第二层: 技术面专家")
    print(f"{'='*65}")
    
    tech_agent = AgentTechnical()
    tech_result = tech_agent.analyze(df)
    
    print(f"  技术面评分: {tech_result['score']}/100")
    print(f"  信号: {tech_result['signal']}")
    print(f"  指标:")
    for k, v in tech_result['indicators'].items():
        print(f"    • {k}: {v}")
    
    # ========== 第三层: 决策委员会 ==========
    print(f"\n{'='*65}")
    print(f"  🏛️ 第三层: 决策委员会")
    print(f"{'='*65}")
    
    committee = DecisionCommittee()
    vote_result = committee.vote(tech_result, tactic_summary, name, code)
    committee.print_report(vote_result, tech_result, tactic_summary, name, code)
    
    return {
        'stock': {'code': code, 'name': name},
        'timestamp': datetime.now().isoformat(),
        'tactic_results': tactic_results,
        'tactic_summary': tactic_summary,
        'technical': tech_result,
        'committee': vote_result
    }


# ==================== 批量分析 ============
def analyze_stocks_batch(stocks: List[tuple]) -> List[Dict]:
    """
    批量分析多只股票
    
    Args:
        stocks: [(code, name), ...]
    """
    results = []
    for code, name in stocks:
        print(f"\n\n{'#'*70}")
        print(f"#  分析: {name}({code})")
        print(f"{'#'*70}")
        
        result = analyze_stock_full(code, name)
        if result:
            results.append(result)
    
    return results


# ==================== 测试 ============
if __name__ == "__main__":
    # 测试单只股票
    print("\n" + "="*70)
    print("  🏛️ 虾米专业级股票决策系统 - 三层智能体架构")
    print("="*70)
    
    result = analyze_stock_full("600519", "贵州茅台")
    
    bs.logout()
