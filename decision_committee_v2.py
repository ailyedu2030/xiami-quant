#!/usr/bin/env python3
"""
虾米决策委员会 - 整合5个专项研究智能体的报告

5个专项智能体：
1. 缠论专家 - 三类买点
2. 支撑阻力专家 - 支撑阻力位
3. 形态专家 - K线形态
4. 均线专家 - 均线战法
5. 短线专家 - 尾盘+隔夜+换手率

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research/')

from tactic_research_agents import (
    AgentChanlun, AgentSupportResistance, AgentPattern,
    AgentMovingAverage, AgentShortTerm, get_realtime_price
)
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional


def get_stock_data(code: str, days: int = 90) -> pd.DataFrame:
    """获取股票历史数据"""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        symbol, 'date,open,high,low,close,volume,pctChg',
        start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
        end_date='2026-04-09', frequency='d', adjustflag='2'
    )
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    df = pd.DataFrame(data, columns=rs.fields)
    for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()


def run_all_agents(code: str, name: str, df: pd.DataFrame, realtime: Dict) -> Dict:
    """运行所有5个专项智能体"""
    
    agents = {
        '缠论': AgentChanlun(),
        '支撑阻力': AgentSupportResistance(),
        '形态': AgentPattern(),
        '均线': AgentMovingAverage(),
        '短线': AgentShortTerm(),
    }
    
    results = {}
    
    for agent_name, agent in agents.items():
        try:
            report = agent.research(code, df, realtime)
            results[agent_name] = {
                'report': report,
                'score': report.get('战法评分', 0),
                'confidence': report.get('置信度', '低'),
                'signal': extract_signal(report)
            }
        except Exception as e:
            results[agent_name] = {
                'error': str(e),
                'score': 0
            }
    
    return results


def extract_signal(report: Dict) -> str:
    """从报告中提取信号"""
    if '建议买入点' in report:
        buy = report.get('建议买入点')
        if buy and isinstance(buy, (int, float)):
            return f"买入点: {buy:.2f}"
    
    if '缠论信号' in report:
        signal = report.get('缠论信号', '')
        if '✅' in str(signal):
            return str(signal)
    
    if '均线信号' in report:
        signal = report.get('均线信号', '')
        if '✅' in str(signal):
            return str(signal)
    
    return "信号待确认"


class DecisionCommittee:
    """决策委员会 - 最终裁决机构"""
    
    def __init__(self):
        self.members = ['缠论', '支撑阻力', '形态', '均线', '短线']
    
    def vote(self, agent_results: Dict) -> Dict:
        """投票决策"""
        votes = {}
        total_score = 0
        total_weight = 0
        
        for member in self.members:
            result = agent_results.get(member, {})
            score = result.get('score', 0)
            
            confidence = result.get('confidence', '低')
            if confidence == '高':
                weight = 1.2
            elif confidence == '中':
                weight = 1.0
            else:
                weight = 0.7
            
            weighted_score = score * weight
            total_score += weighted_score
            total_weight += weight
            
            if score >= 70:
                vote = '🟢 强烈买入'
            elif score >= 55:
                vote = '🟡 建议买入'
            elif score >= 40:
                vote = '🟡 观望'
            else:
                vote = '🔴 不建议'
            
            votes[member] = {
                'score': score,
                'weighted_score': weighted_score,
                'vote': vote,
                'signal': result.get('signal', '')
            }
        
        final_score = total_score / total_weight if total_weight > 0 else 0
        
        buy_votes = sum(1 for v in votes.values() if '🟢' in v['vote'])
        hold_votes = sum(1 for v in votes.values() if '🟡' in v['vote'])
        sell_votes = sum(1 for v in votes.values() if '🔴' in v['vote'])
        
        if buy_votes >= 4 and final_score >= 65:
            decision = "🟢 强烈买入"
            action = "重仓参与，止损明确"
        elif buy_votes >= 3 and final_score >= 55:
            decision = "🟢 建议买入"
            action = "适当参与，控制仓位"
        elif buy_votes >= 2 and final_score >= 50:
            decision = "🟡 谨慎买入"
            action = "轻仓试探，严格止损"
        elif hold_votes >= 3:
            decision = "🟡 观望"
            action = "等待更好时机"
        elif sell_votes >= 3:
            decision = "🔴 建议回避"
            action = "不参与，规避风险"
        else:
            decision = "⚪ 方向不明"
            action = "等待明确信号"
        
        return {
            'votes': votes,
            'final_score': round(final_score, 1),
            'buy_votes': buy_votes,
            'hold_votes': hold_votes,
            'sell_votes': sell_votes,
            'decision': decision,
            'action': action
        }
    
    def print_final_report(self, code: str, name: str, realtime: Dict,
                          agent_results: Dict, vote_result: Dict):
        """打印最终决策报告"""
        
        price = realtime.get('price', 0)
        pct = realtime.get('pct', 0)
        
        print(f"\n{'#'*70}")
        print(f"#  🏛️ 虾米决策委员会 - 最终裁决")
        print(f"{'#'*70}")
        print(f"\n股票: {name}({code})")
        print(f"当前价: {price:.2f}元 ({pct:+.2f}%)")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}")
        
        print("\n【各专项智能体分析】")
        print(f"{'-'*70}")
        
        for member in self.members:
            result = agent_results.get(member, {})
            if 'error' in result:
                print(f"  {member}专家: ❌ {result['error']}")
                continue
            
            report = result.get('report', {})
            score = result.get('score', 0)
            signal = result.get('signal', '')
            
            emoji = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴")
            
            print(f"\n  {emoji} {member}专家 | 评分: {score:>3}/100")
            print(f"     信号: {signal}")
            
            if member == '缠论':
                if '第一类买点' in report and report['第一类买点']:
                    print(f"     一买: {report['第一类买点']} | 二买: {report.get('第二类买点', 'N/A')}")
            elif member == '支撑阻力':
                if '建议买入点' in report:
                    print(f"     买入点: {report['建议买入点']} | 止损: {report.get('建议止损位', 'N/A')}")
                    print(f"     上涨空间: {report.get('上涨空间', 'N/A')} | 风险回报: {report.get('风险回报比', 'N/A')}")
            elif member == '均线':
                print(f"     MA5: {report.get('MA5', 'N/A')} | MA20: {report.get('MA20', 'N/A')}")
                print(f"     {report.get('均线信号', '')}")
        
        print(f"\n{'='*70}")
        print("【投票结果】")
        print(f"{'='*70}")
        print(f"  缠论委员:   {vote_result['votes'].get('缠论', {}).get('vote', 'N/A')}")
        print(f"  支撑阻力委员: {vote_result['votes'].get('支撑阻力', {}).get('vote', 'N/A')}")
        print(f"  形态委员:   {vote_result['votes'].get('形态', {}).get('vote', 'N/A')}")
        print(f"  均线委员:   {vote_result['votes'].get('均线', {}).get('vote', 'N/A')}")
        print(f"  短线委员:   {vote_result['votes'].get('短线', {}).get('vote', 'N/A')}")
        print(f"{'-'*70}")
        print(f"  买入票: {vote_result['buy_votes']}  |  观望票: {vote_result['hold_votes']}  |  回避票: {vote_result['sell_votes']}")
        print(f"  加权评分: {vote_result['final_score']}/100")
        print(f"{'='*70}")
        
        decision = vote_result['decision']
        action = vote_result['action']
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🏛️ 最终裁决: {decision:<30}         ║
║                                                              ║
║   💡 操作建议: {action:<30}              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝""")
        
        if '买入' in decision:
            buy_points = []
            stop_losses = []
            targets = []
            
            for member in self.members:
                result = agent_results.get(member, {})
                if 'error' in result:
                    continue
                report = result.get('report', {})
                
                buy = report.get('建议买入点')
                if buy and isinstance(buy, (int, float)):
                    buy_points.append(float(buy))
                stop = report.get('建议止损位')
                if stop and isinstance(stop, (int, float)):
                    stop_losses.append(float(stop))
                tgt = report.get('目标位')
                if tgt and isinstance(tgt, (int, float)):
                    targets.append(float(tgt))
            
            if buy_points:
                avg_buy = sum(buy_points) / len(buy_points)
                avg_stop = min(stop_losses) if stop_losses else price * 0.95
                avg_target = max(targets) if targets else price * 1.08
                
                print(f"""
╔══════════════════════════════════════════════════════════════╗
║  📋 操作明细                                                 ║
╠══════════════════════════════════════════════════════════════╣
║  建议买入点: {avg_buy:.2f}元                                        ║
║  止损位: {avg_stop:.2f}元                                          ║
║  目标位: {avg_target:.2f}元 (+{(avg_target/avg_buy-1)*100:.1f}%)                              ║
║  仓位建议: {'30%' if '谨慎' in decision else '50%'}                                          ║
╚══════════════════════════════════════════════════════════════╝""")


def analyze_stock_professional(code: str, name: str = "") -> Optional[Dict]:
    """专业级股票分析 - 5个智能体 + 决策委员会"""
    
    print(f"\n{'='*70}")
    print(f"  🔬 虾米专业分析系统启动")
    print(f"  股票: {code} {'('+name+')' if name else ''}")
    print(f"{'='*70}")
    
    df = get_stock_data(code)
    if df is None or len(df) < 30:
        print(f"❌ 数据不足")
        return None
    
    realtime = get_realtime_price([f"{'sh' if code.startswith('6') else 'sz'}{code}"])
    rt_data = realtime.get(code, {})
    
    if not rt_data:
        print("⚠️ 实时行情获取失败，使用昨日收盘价")
        rt_data = {'price': df['close'].iloc[-1], 'pct': 0, 'high': df['high'].iloc[-1], 'low': df['low'].iloc[-1]}
    
    print(f"\n🎯 运行5个专项研究智能体...")
    agent_results = run_all_agents(code, name, df, rt_data)
    
    print(f"\n🏛️ 提交决策委员会...")
    committee = DecisionCommittee()
    vote_result = committee.vote(agent_results)
    
    committee.print_final_report(code, name, rt_data, agent_results, vote_result)
    
    return {
        'code': code,
        'name': name,
        'realtime': rt_data,
        'agent_results': agent_results,
        'vote_result': vote_result
    }


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("#  🏛️ 虾米专业级股票分析系统 - 5智能体+决策委员会")
    print("#"*70)
    
    result = analyze_stock_professional("000977", "浪潮信息")
    
    bs.logout()
