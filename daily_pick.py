#!/usr/bin/env python3
"""
虾米每日选股系统 - 每日精选买入机会

每天早上运行，筛选出符合买入条件的股票：
1. 热门板块追踪（不扫冷门股）
2. 四大战法共振筛选
3. 最佳买入点 + 止损位 计算
4. 直接可执行的操作建议

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research/')

from tactic_agents import (
    Agent2560, AgentClosingTime, AgentChips, AgentOvernight,
    TacticAgentFactory, TacticSummary
)


# ==================== 热门板块定义 ====================
HOT_SECTORS = {
    "AI人工智能": ["002230", "002415", "000977", "688041", "300308", "300474", "688339"],
    "新能源车": ["300750", "002594", "300014", "688981", "603986", "600733"],
    "半导体": ["688012", "688981", "002371", "603986", "688008"],
    "军工": ["600760", "600893", "002025", "300699", "002013"],
    "白酒消费": ["600519", "000858", "000568", "603288"],
    "银行": ["600036", "000001", "601318", "600000"],
}


# ==================== 选股标准 ====================
BUY_THRESHOLDS = {
    "min_tactic_score": 50,      # 战术层最低评分
    "min_technical_score": 60,  # 技术面最低评分
    "min_buy_votes": 2,         # 最少买入票数
    "min_rsi": 35,              # RSI最低（不过冷）
    "max_rsi": 65,              # RSI最高（不过热）
    "max_volatility": 8,        # ATR最大波动率%
    "profit_target_pct": 8,     # 盈利目标%
    "stop_loss_pct": 5,         # 止损幅度%
}


def get_stock_data(code: str, days: int = 60) -> Optional[pd.DataFrame]:
    """获取股票数据"""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    try:
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
        
        if len(data) < 30:
            return None
        
        df = pd.DataFrame(data, columns=rs.fields)
        for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna()
    except:
        return None


def calculate_technical_score(df: pd.DataFrame) -> Tuple[int, Dict]:
    """计算技术面评分"""
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
    
    # 布林带
    bb_mid = close.rolling(20).mean().iloc[-1]
    bb_std = close.rolling(20).std().iloc[-1]
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_position = (close.iloc[-1] - bb_lower) / (bb_upper - bb_lower) * 100
    
    # ATR
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    atr_pct = atr / close.iloc[-1] * 100
    
    # 成交量比
    vol_ma5 = volume.rolling(5).mean().iloc[-1]
    vol_ratio = volume.iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
    
    # 综合评分
    score = 0
    indicators = {}
    
    if ma_bullish:
        score += 25
        indicators['均线多头'] = '✅'
    else:
        indicators['均线多头'] = '❌'
    
    if macd_bullish:
        score += 25
        indicators['MACD'] = '✅'
    else:
        indicators['MACD'] = '❌'
    
    if 40 <= rsi <= 60:
        score += 20
    indicators['RSI'] = f'{rsi:.1f}'
    
    if vol_ratio >= 1.2:
        score += 15
        indicators['放量'] = f'✅ {vol_ratio:.2f}x'
    else:
        indicators['放量'] = f'❌ {vol_ratio:.2f}x'
    
    if atr_pct <= 5:
        score += 15
        indicators['波动率'] = f'✅ 低'
    else:
        indicators['波动率'] = f'⚠️ {atr_pct:.1f}%'
    
    return min(100, score), {
        **indicators,
        'RSI': round(rsi, 1),
        'ATR%': round(atr_pct, 2),
        '布林位置': round(bb_position, 1),
        '当前价': round(close.iloc[-1], 2)
    }


def analyze_stock_pick(code: str, name: str) -> Optional[Dict]:
    """分析单只股票是否值得买入"""
    df = get_stock_data(code)
    if df is None:
        return None
    
    close = df['close']
    price = close.iloc[-1]
    
    # 技术面评分
    tech_score, tech_indicators = calculate_technical_score(df)
    
    # 战术层评分
    try:
        agents = {
            '2560': Agent2560(),
            'closing': AgentClosingTime(),
            'chips': AgentChips(),
            'overnight': AgentOvernight()
        }
        
        tactic_scores = []
        tactic_signals = []
        
        for tactic_name, agent in agents.items():
            result = agent.analyze(df)
            tactic_scores.append(result.get('score', 0))
            tactic_signals.append(result.get('signal', '⚪'))
        
        tactic_avg = sum(tactic_scores) / len(tactic_scores)
        tactic_buy_count = sum(1 for s in tactic_signals if '🟢' in s)
        
    except Exception as e:
        tactic_avg = 50
        tactic_buy_count = 1
    
    # RSI检查
    rsi = tech_indicators.get('RSI', 50)
    rsi_ok = BUY_THRESHOLDS["min_rsi"] <= rsi <= BUY_THRESHOLDS["max_rsi"]
    
    # ATR检查
    atr_pct = tech_indicators.get('ATR%', 5)
    atr_ok = atr_pct <= BUY_THRESHOLDS["max_volatility"]
    
    # 计算买入点
    ma5 = close.rolling(5).mean().iloc[-1]
    ma10 = close.rolling(10).mean().iloc[-1]
    
    # 最佳买入点：回调到MA5或MA10附近
    if price > ma5 * 0.98:
        entry_point = round(ma5, 2)
        entry_type = "MA5支撑"
    elif price > ma10 * 0.98:
        entry_point = round(ma10, 2)
        entry_type = "MA10支撑"
    else:
        entry_point = round(price * 0.99, 2)
        entry_type = "现价介入"
    
    # 止损位
    stop_loss = round(entry_point * (1 - BUY_THRESHOLDS["stop_loss_pct"] / 100), 2)
    
    # 目标位
    target_price = round(entry_point * (1 + BUY_THRESHOLDS["profit_target_pct"] / 100), 2)
    
    # 上涨空间
    upside = (target_price - entry_point) / entry_point * 100
    risk_ratio = upside / BUY_THRESHOLDS["stop_loss_pct"]
    
    # 综合评分
    final_score = (tech_score * 0.4 + tactic_avg * 0.6)
    
    # 买入信号
    buy_score = 0
    if tech_score >= BUY_THRESHOLDS["min_technical_score"]:
        buy_score += 1
    if tactic_avg >= BUY_THRESHOLDS["min_tactic_score"]:
        buy_score += 1
    if tactic_buy_count >= BUY_THRESHOLDS["min_buy_votes"]:
        buy_score += 1
    if rsi_ok and atr_ok:
        buy_score += 1
    
    if buy_score >= 3 and final_score >= 55:
        signal = "🟢 强烈推荐"
        priority = 1
    elif buy_score >= 2 and final_score >= 50:
        signal = "🟡 谨慎推荐"
        priority = 2
    elif buy_score >= 2:
        signal = "🟡 观察"
        priority = 3
    else:
        signal = "⚪ 观望"
        priority = 9
    
    return {
        'code': code,
        'name': name,
        'price': round(price, 2),
        'signal': signal,
        'priority': priority,
        'final_score': round(final_score, 1),
        'tech_score': tech_score,
        'tactic_avg': round(tactic_avg, 1),
        'tactic_buy_count': tactic_buy_count,
        'rsi': rsi,
        'rsi_ok': rsi_ok,
        'atr_pct': atr_pct,
        'entry_point': entry_point,
        'entry_type': entry_type,
        'stop_loss': stop_loss,
        'target_price': target_price,
        'upside': round(upside, 1),
        'risk_ratio': round(risk_ratio, 1),
        'indicators': tech_indicators
    }


def scan_hot_sectors() -> List[Dict]:
    """扫描热门板块，筛选买入机会"""
    results = []
    
    print(f"\n{'='*65}")
    print(f"  🔥 虾米每日选股系统 - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*65}")
    print(f"  扫描范围: {len(HOT_SECTORS)} 大热门板块")
    print(f"  总股票数: {sum(len(v) for v in HOT_SECTORS.values())} 只")
    print(f"{'='*65}")
    
    for sector_name, codes in HOT_SECTORS.items():
        print(f"\n  📊 扫描中: {sector_name}...", end=" ", flush=True)
        sector_picks = []
        
        for code in codes:
            pick = analyze_stock_pick(code, code)  # name will be updated
            if pick and pick['signal'] != '⚪ 观望':
                # 获取股票名称（从已知列表，这里简化处理）
                if code == "002230": pick['name'] = "科大讯飞"
                elif code == "002415": pick['name'] = "海康威视"
                elif code == "000977": pick['name'] = "浪潮信息"
                elif code == "688041": pick['name'] = "寒武纪"
                elif code == "300750": pick['name'] = "宁德时代"
                elif code == "002594": pick['name'] = "比亚迪"
                elif code == "300014": pick['name'] = "亿纬锂能"
                elif code == "688981": pick['name'] = "中芯国际"
                elif code == "603986": pick['name'] = "兆易创新"
                elif code == "688012": pick['name'] = "中微公司"
                elif code == "002371": pick['name'] = "北方华创"
                elif code == "688008": pick['name'] = "澜起科技"
                elif code == "600760": pick['name'] = "中航沈飞"
                elif code == "600893": pick['name'] = "航发动力"
                elif code == "002025": pick['name'] = "航天电器"
                elif code == "300699": pick['name'] = "光威复材"
                elif code == "002013": pick['name'] = "中航机电"
                elif code == "600519": pick['name'] = "贵州茅台"
                elif code == "000858": pick['name'] = "五粮液"
                elif code == "000568": pick['name'] = "泸州老窖"
                elif code == "603288": pick['name'] = "海天味业"
                elif code == "600036": pick['name'] = "招商银行"
                elif code == "000001": pick['name'] = "平安银行"
                elif code == "601318": pick['name'] = "中国平安"
                elif code == "600000": pick['name'] = "浦发银行"
                elif code == "300308": pick['name'] = "中际旭创"
                elif code == "300474": pick['name'] = "景嘉微"
                elif code == "688339": pick['name'] = "奇安信"
                elif code == "600733": pick['name'] = "北汽蓝谷"
                
                pick['sector'] = sector_name
                sector_picks.append(pick)
        
        print(f"完成 ({len(sector_picks)} 个候选)")
        results.extend(sector_picks)
    
    # 按评分排序
    results.sort(key=lambda x: (x['priority'], -x['final_score']))
    
    return results


def print_daily_report(picks: List[Dict]):
    """打印每日选股报告"""
    print(f"\n\n{'#'*70}")
    print(f"  📋 虾米每日精选 - 可买入股票名单")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*70}")
    
    # 强烈推荐
    strong_buys = [p for p in picks if p['signal'] == '🟢 强烈推荐']
    cautious_buys = [p for p in picks if p['signal'] == '🟡 谨慎推荐']
    
    if strong_buys:
        print(f"\n🟢 强烈推荐买入 ({len(strong_buys)} 只)")
        print(f"  {'─'*65}")
        for p in strong_buys:
            print(f"""
  📈 {p['name']}({p['code']}) - {p['sector']}
     价格: {p['price']:.2f}元 | 评分: {p['final_score']}/100
     🎯 买入点: {p['entry_point']:.2f}元 ({p['entry_type']})
     🛡️ 止损位: {p['stop_loss']:.2f}元 (跌{p['atr_pct']*2:.1f}%)
     📊 技术: {p['tech_score']}分 | 战术: {p['tactic_avg']}分
     💡 RSI: {p['rsi']} | 风险回报比: 1:{p['risk_ratio']}
     🔥 战法共振: {p['tactic_buy_count']}个战法看涨""")
    
    if cautious_buys:
        print(f"\n🟡 谨慎推荐 ({len(cautious_buys)} 只)")
        print(f"  {'─'*65}")
        for p in cautious_buys:
            print(f"""
  📈 {p['name']}({p['code']}) - {p['sector']}
     价格: {p['price']:.2f}元 | 评分: {p['final_score']}/100
     🎯 买入点: {p['entry_point']:.2f}元 ({p['entry_type']})
     🛡️ 止损位: {p['stop_loss']:.2f}元""")
    
    if not picks:
        print(f"""
  ⚪ 今日扫描结果
  
  暂无符合条件的买入机会
  
  💡 建议:
  • 等待市场回调后再次扫描
  • 关注明日开盘后的机会
  • 大盘趋势向好时机会更多""")
    
    # 总结
    print(f"\n{'='*70}")
    print(f"  📊 扫描统计")
    print(f"  ────────────────────────────────────")
    print(f"  热门板块: {len(HOT_SECTORS)} 个")
    print(f"  扫描股票: {sum(len(v) for v in HOT_SECTORS.values())} 只")
    print(f"  强烈推荐: {len(strong_buys)} 只")
    print(f"  谨慎推荐: {len(cautious_buys)} 只")
    print(f"  观望: {len(picks) - len(strong_buys) - len(cautious_buys)} 只")
    print(f"{'='*70}")
    
    # 操作建议
    if strong_buys:
        top = strong_buys[0]
        print(f"""
  🏆 今日最佳买入
  ────────────────────────────────────
  股票: {top['name']}({top['code']})
  板块: {top['sector']}
  当前价: {top['price']:.2f}元
  建议买入点: {top['entry_point']:.2f}元
  止损位: {top['stop_loss']:.2f}元
  目标位: {top['target_price']:.2f}元
  预期涨幅: +{top['upside']}%
  风险回报比: 1:{top['risk_ratio']}
  ────────────────────────────────────""")
    
    return picks


# ==================== 主程序 ====================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("  🔥 虾米每日选股系统启动")
    print("  专注热门板块，精准买入")
    print("="*70)
    
    # 扫描热门板块
    picks = scan_hot_sectors()
    
    # 打印报告
    print_daily_report(picks)
    
    bs.logout()
