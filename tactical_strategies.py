#!/usr/bin/env python3
"""
经典战法系统 - 专业级短线战术实现

包含：
1. 2560战法 - 安德烈·昂格尔传奇策略
2. 尾盘买入法 - 14:30选股战术
3. 筹码战法 - 筹码分布分析
4. 隔夜持股法 - 短周期套利策略
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# ==================== 战法1: 2560战法 ====================
class Strategy2560:
    """
    2560战法 - 传奇短线大师安德烈·昂格尔的致胜策略
    
    核心指标：
    - 25日均线（MA25）：判断趋势方向
    - 5日均量（VOL_MA5）：短期量能
    - 60日均量（VOL_MA60）：中长期量能
    
    买入条件：
    1. MA25 必须向上
    2. VOL_MA5 上穿 VOL_MA60（金叉）
    
    卖出条件：
    1. VOL_MA5 下穿 VOL_MA60（死叉）
    2. 或 MA25 开始走平/向下
    """
    
    def __init__(self):
        self.name = "2560战法"
        self.author = "安德烈·昂格尔"
        
    def calculate(self, df: pd.DataFrame) -> Dict:
        """计算2560战法指标"""
        close = df['close']
        volume = df['volume']
        
        results = {}
        
        # MA25 - 25日均线
        ma25 = close.rolling(25).mean()
        results['ma25'] = round(ma25.iloc[-1], 2)
        results['ma25_trend'] = 'up' if ma25.iloc[-1] > ma25.iloc[-5] else 'down'
        results['ma25_slope'] = round((ma25.iloc[-1] - ma25.iloc[-5]) / ma25.iloc[-5] * 100, 2)
        
        # VOL_MA5 - 5日均量
        vol_ma5 = volume.rolling(5).mean()
        results['vol_ma5'] = round(vol_ma5.iloc[-1], 0)
        
        # VOL_MA60 - 60日均量
        vol_ma60 = volume.rolling(60).mean()
        results['vol_ma60'] = round(vol_ma60.iloc[-1], 0)
        
        # 量能金叉/死叉检测
        vol_now = vol_ma5.iloc[-1]
        vol_prev = vol_ma5.iloc[-2]
        vol_60_now = vol_ma60.iloc[-1]
        vol_60_prev = vol_ma60.iloc[-2]
        
        # 金叉：VOL_MA5 从下方穿越 VOL_MA60
        results['vol_golden_cross'] = vol_prev < vol_60_prev and vol_now > vol_60_now
        # 死叉：VOL_MA5 从上方穿越 VOL_MA60
        results['vol_death_cross'] = vol_prev > vol_60_prev and vol_now < vol_60_now
        
        # 当前价格与MA25关系
        results['price_vs_ma25'] = 'above' if close.iloc[-1] > ma25.iloc[-1] else 'below'
        
        # 买入条件判断
        buy_condition_1 = results['ma25_trend'] == 'up'  # MA25向上
        buy_condition_2 = results['vol_golden_cross']  # 量能金叉
        
        results['buy_signal'] = buy_condition_1 and buy_condition_2
        results['sell_signal'] = results['vol_death_cross'] or results['ma25_trend'] == 'down'
        
        # 仓位建议
        if results['buy_signal']:
            results['action'] = "🟢 买入"
        elif results['vol_golden_cross'] and not buy_condition_1:
            results['action'] = "🟡 关注（MA25未向上）"
        elif results['sell_signal']:
            results['action'] = "🔴 卖出"
        else:
            results['action'] = "⚪ 观望"
        
        # 风险提示
        results['risk'] = []
        if close.iloc[-1] > ma25.iloc[-1] * 1.1:
            results['risk'].append("价格偏离MA25过远，注意回调")
        if results['vol_golden_cross']:
            results['risk'].append("量能金叉，需确认持续性")
        
        return results
    
    def analyze(self, df: pd.DataFrame, name: str = "") -> str:
        """输出分析报告"""
        r = self.calculate(df)
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 {self.name} - {self.author}                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📈 核心指标                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  MA25（25日均线）: {r.get('ma25', 'N/A'):>10}                        ║
║  MA25趋势: {r.get('ma25_trend', 'N/A'):>8} | 斜率: {r.get('ma25_slope', 'N/A'):>6}%        ║
║  价格位置: {'线上 ✅' if r.get('price_vs_ma25') == 'above' else '线下 ⚠️'}                                       ║
║                                                              ║
║  📊 量能指标                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  VOL_MA5:  {r.get('vol_ma5', 'N/A'):>10.0f}                              ║
║  VOL_MA60: {r.get('vol_ma60', 'N/A'):>10.0f}                              ║
║                                                              ║
║  {'✅ 量能金叉！' if r.get('vol_golden_cross') else '➖ 量能状态正常'}

║                                                              ║
║  📋 战法信号                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  买入条件1（MA25向上）: {'✅ 满足' if r.get('ma25_trend') == 'up' else '❌ 不满足'}                           ║
║  买入条件2（量能金叉）: {'✅ 满足' if r.get('vol_golden_cross') else '❌ 不满足'}                           ║
║                                                              ║
║  ═══════════════════════════════════════════════════════════  ║
║  🎯 最终信号: {r.get('action', 'N/A'):<20}                    ║
║  ═══════════════════════════════════════════════════════════  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report


# ==================== 战法2: 尾盘买入法 ====================
class StrategyClosingTime:
    """
    尾盘买入法 - 14:30-15:00选股战术
    
    核心逻辑：
    - 尾盘是多空决策的关键窗口
    - 主力资金往往在尾盘完成布局
    - 选取强势股，次日开盘/早盘卖出
    
    选股条件：
    1. 涨幅3%-5%（太低无力，太高追高风险）
    2. 量比>1.5（资金活跃）
    3. 股价在MA5上方（趋势强劲）
    4. K线形态良好（阳线收盘）
    5. 流通市值适中（10-500亿）
    """
    
    def __init__(self):
        self.name = "尾盘买入法"
        self.timing = "14:30-15:00"
        
    def calculate(self, df: pd.DataFrame) -> Dict:
        """计算尾盘买入法指标"""
        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        results = {}
        price = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        # 今日涨幅
        results['pct_change'] = round((price - prev_close) / prev_close * 100, 2)
        
        # 涨幅区间判断
        pct = results['pct_change']
        if 3 <= pct <= 5:
            results['pct_range'] = "最佳区间 ✅"
        elif 2 <= pct < 3:
            results['pct_range'] = "偏低 🟡"
        elif 5 < pct <= 7:
            results['pct_range'] = "偏高 🔴"
        else:
            results['pct_range'] = "超出范围"
        
        # 量比（简化：用成交量/均量）
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        results['vol_ratio'] = round(volume.iloc[-1] / vol_ma5, 2) if vol_ma5 > 0 else 1
        results['vol_ok'] = results['vol_ratio'] > 1.5
        
        # MA5位置
        ma5 = close.rolling(5).mean().iloc[-1]
        results['ma5'] = round(ma5, 2)
        results['above_ma5'] = price > ma5
        
        # K线形态
        body = price - open_price.iloc[-1]
        body_pct = body / prev_close * 100
        upper_shadow = high.iloc[-1] - max(price, open_price.iloc[-1])
        lower_shadow = min(price, open_price.iloc[-1]) - low.iloc[-1]
        
        results['kline_body'] = round(body_pct, 2)
        results['kline_type'] = "阳线 ✅" if body > 0 else "阴线 ⚠️"
        results['kline_quality'] = "良好 ✅" if body > 0 and upper_shadow < body * 0.5 else "一般 🟡"
        
        # 尾盘强势信号
        # 条件：14:00后股价持续在高位
        if len(df) >= 4:
            afternoon_prices = close.iloc[-4:]
            results['afternoon_strength'] = all(afternoon_prices.iloc[i] >= afternoon_prices.iloc[i-1] for i in range(1, len(afternoon_prices)))
        else:
            results['afternoon_strength'] = False
        
        # 综合评分（尾盘强势度）
        score = 0
        if 3 <= pct <= 5: score += 30
        elif 2 <= pct <= 7: score += 20
        
        if results['vol_ok']: score += 25
        if results['above_ma5']: score += 20
        if body > 0: score += 15
        if results.get('afternoon_strength'): score += 10
        
        results['closing_score'] = min(100, score)
        
        # 买入建议
        if results['closing_score'] >= 70:
            results['action'] = "🟢 强烈建议尾盘买入"
        elif results['closing_score'] >= 50:
            results['action'] = "🟡 可考虑买入"
        elif results['closing_score'] >= 30:
            results['action'] = "⚪ 观望"
        else:
            results['action'] = "❌ 不建议买入"
        
        # 风险提示
        results['risk'] = []
        if pct > 7:
            results['risk'].append("涨幅过大，追高风险高")
        if results['vol_ratio'] > 3:
            results['risk'].append("成交量异常放大，小心对倒")
        if body < 0:
            results['risk'].append("尾盘收阴，多头乏力")
        
        return results
    
    def analyze(self, df: pd.DataFrame, name: str = "") -> str:
        """输出分析报告"""
        r = self.calculate(df)
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 {self.name} - 尾盘选股战术                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ⏰ 尾盘时间: 14:30-15:00                                   ║
║                                                              ║
║  📈 涨幅分析                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  今日涨幅: {r.get('pct_change', 'N/A'):>6.2f}%                                    ║
║  涨幅区间: {r.get('pct_range', 'N/A'):<15}                               ║
║  K线形态: {r.get('kline_type', 'N/A'):<8} | 实体: {r.get('kline_body', 'N/A'):>5.2f}%                     ║
║                                                              ║
║  📊 量能分析                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  量比: {r.get('vol_ratio', 'N/A'):>6.2f} {'✅ 放量' if r.get('vol_ok') else '❌ 缩量'}                              ║
║  MA5: {r.get('ma5', 'N/A'):>10.2f}                                          ║
║  价格vsMA5: {'线上 ✅' if r.get('above_ma5') else '线下 ⚠️'}                                       ║
║                                                              ║
║  🎯 尾盘强势度评分: {r.get('closing_score', 'N/A'):>3}/100                               ║
║                                                              ║
║  ═══════════════════════════════════════════════════════════  ║
║  🎯 最终建议: {r.get('action', 'N/A'):<25}               ║
║  ═══════════════════════════════════════════════════════════  ║
║                                                              ║
║  ⚠️ 风险提示:                                                 ║
║  {'  '.join(r.get('risk', ['无明显风险']))}         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report


# ==================== 战法3: 筹码战法 ====================
class StrategyChips:
    """
    筹码战法 - 筹码分布分析战术
    
    核心概念：
    - 筹码峰（Chip Peak）：筹码最密集的区域，代表支撑/压力位
    - 筹码集中度：70%筹码集中度、90%筹码集中度
    - 获利盘比例：当前价格以上的筹码占比
    
    选股逻辑：
    1. 筹码集中度<10%（高度集中，主力控盘）
    2. 筹码峰在当前价格下方（上行空间大）
    3. 获利盘适中（20%-80%最佳）
    4. 底部筹码密集（主力吸筹完成）
    """
    
    def __init__(self):
        self.name = "筹码战法"
        
    def estimate_chips(self, df: pd.DataFrame) -> Dict:
        """
        估算筹码分布（简化模型）
        注意：真实筹码需要Level2数据，这里用价格分布模拟
        """
        close = df['close']
        volume = df['volume']
        
        results = {}
        
        # 计算价格区间的筹码分布
        # 使用 histogram 方法模拟
        price_min = close.min() * 0.9
        price_max = close.max() * 1.1
        bins = 20
        price_range = np.linspace(price_min, price_max, bins)
        
        # 计算每个价格区间的成交量
        chip_dist = []
        for i in range(len(price_range) - 1):
            mask = (close >= price_range[i]) & (close < price_range[i+1])
            vol_sum = volume[mask].sum()
            chip_dist.append({
                'price_low': price_range[i],
                'price_high': price_range[i+1],
                'volume': vol_sum
            })
        
        # 找出筹码峰（最大成交量的价格区间）
        max_vol_idx = max(range(len(chip_dist)), key=lambda x: chip_dist[x]['volume'])
        chip_peak = chip_dist[max_vol_idx]
        results['chip_peak_low'] = round(chip_peak['price_low'], 2)
        results['chip_peak_high'] = round(chip_peak['price_high'], 2)
        results['chip_peak_vol'] = chip_peak['volume']
        
        # 筹码集中度估算
        # 假设最近N天的持仓成本集中在某些价格带
        recent_vol = volume.tail(20).sum()
        peak_vol_pct = chip_peak['volume'] / recent_vol * 100 if recent_vol > 0 else 0
        results['concentration'] = round(peak_vol_pct, 1)
        
        # 获利盘估算（当前价格以上的筹码比例）
        current_price = close.iloc[-1]
        winning_mask = close > current_price * 0.95
        winning_vol = volume[winning_mask].tail(20).sum()
        winning_pct = winning_vol / recent_vol * 100 if recent_vol > 0 else 50
        results['winning_pct'] = round(winning_pct, 1)
        
        # 套牢盘估算（当前价格以下的筹码）
        losing_pct = 100 - winning_pct
        results['losing_pct'] = round(losing_pct, 1)
        
        # 筹码分布形态判断
        if winning_pct > 80:
            results['chip_status'] = "高位派发 ⚠️"
            results['action'] = "❌ 不建议买入"
        elif winning_pct < 20:
            results['chip_status'] = "低位吸筹 ✅"
            results['action'] = "🟢 可关注买入"
        elif losing_pct > 70:
            results['chip_status'] = "上方套牢重压 🔴"
            results['action'] = "⚠️ 谨慎买入"
        else:
            results['chip_status'] = "筹码稳固 💎"
            results['action'] = "🟡 稳健机会"
        
        # 筹码峰位置分析
        mid_price = (chip_peak['price_low'] + chip_peak['price_high']) / 2
        results['peak_position'] = "当前价下方 ✅" if mid_price < current_price * 0.95 else ("当前价附近 ⚖️" if mid_price < current_price * 1.05 else "当前价上方 🔴")
        
        # 集中度评估
        if peak_vol_pct > 40:
            results['concentration_level'] = "高度集中 💎"
            results['concentration_signal'] = "主力控盘迹象"
        elif peak_vol_pct > 25:
            results['concentration_level'] = "适度集中 📊"
            results['concentration_signal'] = "筹码分布良好"
        else:
            results['concentration_level'] = "分散 ⚠️"
            results['concentration_signal'] = "关注度低"
        
        return results
    
    def analyze(self, df: pd.DataFrame, name: str = "") -> str:
        """输出分析报告"""
        r = self.estimate_chips(df)
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 {self.name} - 筹码分布分析                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🎯 筹码分布核心指标                                          ║
║  ─────────────────────────────────────────────────────────  ║
║  筹码峰区间: {r.get('chip_peak_low', 'N/A'):>8.2f} - {r.get('chip_peak_high', 'N/A'):<8.2f}                   ║
║  筹码集中度: {r.get('concentration', 'N/A'):>6.1f}%                                   ║
║  集中度评估: {r.get('concentration_level', 'N/A'):<15}                        ║
║                                                              ║
║  💰 盈亏分析                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  获利盘比例: {r.get('winning_pct', 'N/A'):>6.1f}% {'✅ 适中' if 20 <= r.get('winning_pct', 0) <= 80 else '⚠️ 偏高/偏低'}                        ║
║  套牢盘比例: {r.get('losing_pct', 'N/A'):>6.1f}%                                   ║
║  筹码状态: {r.get('chip_status', 'N/A'):<15}                              ║
║                                                              ║
║  📍 位置分析                                                  ║
║  ─────────────────────────────────────────────────────────  ║
║  筹码峰位置: {r.get('peak_position', 'N/A'):<20}                        ║
║                                                              ║
║  ═══════════════════════════════════════════════════════════  ║
║  🎯 筹码信号: {r.get('action', 'N/A'):<25}               ║
║  ═══════════════════════════════════════════════════════════  ║
║                                                              ║
║  💡 集中度信号: {r.get('concentration_signal', 'N/A'):<20}                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report


# ==================== 战法4: 隔夜持股法 ====================
class StrategyOvernight:
    """
    隔夜持股法 - 短周期套利策略
    
    核心理念：
    - 尾盘买入（14:30-15:00），次日早盘卖出（9:30-10:00）
    - 持股时间短（隔夜），控制风险
    - 利用消息面和资金惯性获利
    
    8步筛选：
    1. 涨幅筛选：3%-7%的强势股
    2. 量比筛选：>1.5
    3. 换手率：>3%
    4. 流通市值：10-500亿
    5. 成交量持续放大
    6. K线形态良好
    7. 突破关键位置
    8. 板块龙头优先
    """
    
    def __init__(self):
        self.name = "隔夜持股法"
        self.buy_time = "14:30-15:00"
        self.sell_time = "次日9:30-10:00"
        
    def calculate(self, df: pd.DataFrame) -> Dict:
        """计算隔夜持股法指标"""
        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        results = {}
        price = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        # 1. 涨幅筛选
        pct = (price - prev_close) / prev_close * 100
        results['pct'] = round(pct, 2)
        results['pct_ok'] = 3 <= abs(pct) <= 7
        
        # 2. 量比
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
        results['vol_ratio'] = round(vol_ratio, 2)
        results['vol_ok'] = vol_ratio > 1.5
        
        # 3. 换手率估算（简化）
        results['turnover_est'] = round(volume.iloc[-1] / volume.mean() * 100, 2) if volume.mean() > 0 else 0
        results['turnover_ok'] = results['turnover_est'] > 3
        
        # 4. 均线多头
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma多头 = ma5 > ma10 > ma20
        results['ma_bullish'] = ma多头
        
        # 5. 成交量趋势（连续放量）
        vol_trend = all(volume.iloc[-i] > volume.iloc[-i-1] for i in range(1, 4))
        results['vol_trend_up'] = vol_trend
        
        # 6. K线形态
        body = price - open_price.iloc[-1]
        is_yangxian = body > 0
        upper_shadow = high.iloc[-1] - max(price, open_price.iloc[-1])
        is_whip = upper_shadow < body * 0.3 if body > 0 else True
        results['kline_good'] = is_yangxian and is_whip
        
        # 7. 突破近期高点
        high_20 = high.tail(20).max()
        results['break_high'] = price > high_20 * 0.98
        
        # 8. 板块龙头（简化：用涨幅排名代替）
        results['is_strong'] = pct > 5 if pct > 0 else False
        
        # 综合评分
        score = 0
        if results['pct_ok']: score += 20
        if results['vol_ok']: score += 15
        if results['ma_bullish']: score += 20
        if results['vol_trend_up']: score += 15
        if results['kline_good']: score += 15
        if results['break_high']: score += 10
        if pct > 0: score += 5
        
        results['overnight_score'] = min(100, score)
        
        # 风险评估
        results['risk'] = []
        if pct > 7:
            results['risk'].append("涨幅过大，隔夜风险高")
        if not results['vol_trend_up']:
            results['risk'].append("量能不能持续，小心一日游")
        if not results['kline_good']:
            results['risk'].append("K线形态不佳")
        
        # 隔夜建议
        if results['overnight_score'] >= 75:
            results['action'] = "🟢 强烈建议隔夜持股"
        elif results['overnight_score'] >= 55:
            results['action'] = "🟡 可考虑隔夜"
        else:
            results['action'] = "❌ 不建议隔夜"
        
        return results
    
    def analyze(self, df: pd.DataFrame, name: str = "") -> str:
        """输出分析报告"""
        r = self.calculate(df)
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 {self.name} - 隔夜套利策略                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ⏰ 买入时间: {self.buy_time}                                  ║
║  ⏰ 卖出时间: {self.sell_time}                              ║
║                                                              ║
║  📋 8步筛选条件                                               ║
║  ─────────────────────────────────────────────────────────  ║
║  1. 涨幅筛选: {r.get('pct', 'N/A'):>6.2f}% {'✅' if r.get('pct_ok') else '❌'}                                ║
║  2. 量比: {r.get('vol_ratio', 'N/A'):>6.2f} {'✅' if r.get('vol_ok') else '❌'}                                ║
║  3. 换手率: {r.get('turnover_est', 'N/A'):>6.2f}% {'✅' if r.get('turnover_ok') else '❌'}                              ║
║  4. 均线多头: {'✅' if r.get('ma_bullish') else '❌'}                                           ║
║  5. 量能持续: {'✅' if r.get('vol_trend_up') else '❌'}                                           ║
║  6. K线良好: {'✅' if r.get('kline_good') else '❌'}                                            ║
║  7. 突破高点: {'✅' if r.get('break_high') else '❌'}                                            ║
║  8. 强势股: {'✅' if r.get('is_strong') else '❌'}                                               ║
║                                                              ║
║  🎯 隔夜评分: {r.get('overnight_score', 'N/A'):>3}/100                               ║
║                                                              ║
║  ═══════════════════════════════════════════════════════════  ║
║  🎯 最终建议: {r.get('action', 'N/A'):<25}               ║
║  ═══════════════════════════════════════════════════════════  ║
║                                                              ║
║  ⚠️ 风险提示: {'  '.join(r.get('risk', ['无明显风险']))}         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report


# ==================== 综合战法分析器 ====================
class TacticalStrategies:
    """综合战法分析器 - 同时运行多种战法"""
    
    def __init__(self):
        self.strategies = {
            "2560战法": Strategy2560(),
            "尾盘买入法": StrategyClosingTime(),
            "筹码战法": StrategyChips(),
            "隔夜持股法": StrategyOvernight()
        }
    
    def analyze_all(self, df: pd.DataFrame, name: str = "") -> Dict:
        """运行所有战法分析"""
        results = {}
        
        for strategy_name, strategy in self.strategies.items():
            try:
                if strategy_name == "2560战法":
                    results[strategy_name] = strategy.calculate(df)
                elif strategy_name == "尾盘买入法":
                    results[strategy_name] = strategy.calculate(df)
                elif strategy_name == "筹码战法":
                    results[strategy_name] = strategy.estimate_chips(df)
                elif strategy_name == "隔夜持股法":
                    results[strategy_name] = strategy.calculate(df)
            except Exception as e:
                results[strategy_name] = {"error": str(e)}
        
        return results
    
    def get_signal(self, results: Dict) -> str:
        """综合各战法给出最终信号"""
        buy_count = 0
        hold_count = 0
        sell_count = 0
        
        for name, r in results.items():
            action = r.get('action', '')
            if '🟢' in action or '买入' in action:
                buy_count += 1
            elif '🟡' in action or '关注' in action or '持有' in action:
                hold_count += 1
            elif '❌' in action or '卖出' in action:
                sell_count += 1
        
        total = buy_count + hold_count + sell_count
        if total == 0:
            return "⚪ 观望"
        
        if buy_count >= 3:
            return "🟢 强烈买入 (多战法共振)"
        elif buy_count >= 2:
            return "🟢 建议买入 (多战法支持)"
        elif hold_count >= 3:
            return "🟡 观望为主"
        elif buy_count >= 1 and hold_count >= 1:
            return "🟡 谨慎买入"
        elif sell_count >= 2:
            return "🔴 建议卖出"
        else:
            return "⚪ 方向不明"
    
    def print_report(self, results: Dict, name: str = "", code: str = ""):
        """打印综合报告"""
        print(f"\n{'='*65}")
        print(f"  📊 虾米战法综合分析 - {name}({code})")
        print(f"{'='*65}")
        
        # 各战法结果
        for strategy_name, r in results.items():
            if 'error' in r:
                print(f"\n❌ {strategy_name}: {r['error']}")
                continue
            
            action = r.get('action', 'N/A')
            score = r.get(f'{strategy_name[:2].lower()}_score' if f'{strategy_name[:2].lower()}_score' in r else 'score', r.get('closing_score', r.get('overnight_score', r.get('concentration', 'N/A'))))
            
            emoji = "🟢" if '🟢' in action else ("🟡" if '🟡' in action else "🔴")
            print(f"\n{emoji} {strategy_name}: {action}")
        
        # 综合信号
        final_signal = self.get_signal(results)
        print(f"\n{'='*65}")
        print(f"  🎯 综合信号: {final_signal}")
        print(f"{'='*65}\n")


def analyze_with_all_strategies(code: str, name: str, df: pd.DataFrame):
    """使用所有战法分析股票"""
    tactics = TacticalStrategies()
    results = tactics.analyze_all(df, name)
    tactics.print_report(results, name, code)
    return results
