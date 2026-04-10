#!/usr/bin/env python3
"""
虾米战法专项研究智能体系统

5个专项智能体，每个深入研究一个战法：
1. 缠论专家 - 三类买点
2. 支撑阻力专家 - 支撑阻力位
3. 形态专家 - K线形态
4. 均线专家 - 均线战法
5. 短线专家 - 尾盘+隔夜+换手率

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import requests


def get_realtime_price(codes: List[str]) -> Dict[str, Dict]:
    """获取实时行情（新浪API）"""
    code_str = ','.join(codes)
    url = f"http://hq.sinajs.cn/list={code_str}"
    headers = {'Referer': 'http://finance.sina.com.cn'}
    
    result = {}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            content = response.text.strip()
            for line in content.split('\n'):
                if '=' in line:
                    raw_code = line.split('=')[0].split('_')[-1]
                    data_part = line.split('="')[1].split('"')[0] if '="' in line else ""
                    if data_part:
                        fields = data_part.split(',')
                        if len(fields) >= 10:
                            code = raw_code[-6:]
                            result[code] = {
                                'name': fields[0],
                                'open': float(fields[1]),
                                'prev_close': float(fields[2]),
                                'price': float(fields[3]),
                                'high': float(fields[4]),
                                'low': float(fields[5]),
                                'vol': float(fields[8]),
                                'amount': float(fields[9]),
                                'pct': (float(fields[3]) - float(fields[2])) / float(fields[2]) * 100
                            }
    except Exception as e:
        print(f"实时行情获取失败: {e}")
    
    return result


class BaseAgent(ABC):
    """战法研究智能体基类"""
    
    def __init__(self, name: str, strategy_name: str, description: str):
        self.name = name
        self.strategy_name = strategy_name
        self.description = description
    
    @abstractmethod
    def research(self, code: str, df: pd.DataFrame, realtime: Dict) -> Dict:
        pass


class AgentChanlun(BaseAgent):
    """缠论专家 - 三类买点"""
    
    def __init__(self):
        super().__init__("缠论专家", "缠论三类买点", "底背离+三类买点")
    
    def research(self, code: str, df: pd.DataFrame, realtime: Dict) -> Dict:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        price = realtime.get('price', close.iloc[-1])
        
        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd_line = exp12 - exp26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        recent20 = close.tail(20)
        recent_macd = histogram.tail(20)
        
        # 找最低价
        lowest_idx = recent20.argmin()
        lowest_price = recent20.min()
        macd_at_low = recent_macd.iloc[lowest_idx]
        macd_min = recent_macd.min()
        
        # 底背离
        price_new_low = lowest_idx > len(recent20) - 5
        macd_not_new_low = macd_at_low > macd_min * 0.5
        divergence = price_new_low and macd_not_new_low
        
        # 第一类买点
        if divergence:
            first_buy = lowest_price
            first_score = 80
        else:
            first_buy = lowest_price
            first_score = 50
        
        # 第二类买点
        recent5_low = close.tail(5).min()
        if first_buy and recent5_low > first_buy * 0.98:
            second_buy = recent5_low
            second_score = 85
        else:
            second_buy = close.iloc[-1] * 0.98
            second_score = 60
        
        # 第三类买点（突破后回踩）
        recent_high = high.tail(20).max()
        if price > recent_high * 0.98:
            third_buy = price * 0.99
            third_score = 75
        else:
            third_buy = recent_high * 1.01
            third_score = 40
        
        # 背驰力度
        if len(recent20) >= 10:
            recent_fall = close.iloc[-1] - close.iloc[-5]
            prev_fall = close.iloc[-5] - close.iloc[-9] if len(close) >= 9 else 0
            div_ratio = recent_fall / prev_fall if prev_fall != 0 else 1
        else:
            div_ratio = 1
        
        # 止损位
        stop_loss = min(first_buy * 0.97, low.tail(20).min() * 1.02)
        
        # 评分
        total = 0
        signals = []
        if first_score >= 70:
            total += first_score
            signals.append("一买信号 ✅")
        if second_score >= 70:
            total += second_score
            signals.append("二买信号 ✅")
        if third_score >= 70:
            total += third_score
            signals.append("三买信号 ✅")
        if div_ratio < 0.8 and div_ratio > 0:
            total += 15
            signals.append(f"底背离(力度{div_ratio:.2f}) ✅")
        
        total = min(100, total // 2 if signals else total)
        
        return {
            "当前价格": price,
            "第一类买点": round(first_buy, 2),
            "一买评分": first_score,
            "第二类买点": round(second_buy, 2),
            "二买评分": second_score,
            "第三类买点": round(third_buy, 2),
            "三买评分": third_score,
            "背离力度": round(div_ratio, 3),
            "建议止损": round(stop_loss, 2),
            "缠论信号": " | ".join(signals) if signals else "暂无明确信号",
            "战法评分": total,
            "置信度": "高" if total >= 70 else ("中" if total >= 50 else "低")
        }


class AgentSupportResistance(BaseAgent):
    """支撑阻力专家"""
    
    def __init__(self):
        super().__init__("支撑阻力专家", "支撑阻力位", "精准计算支撑阻力")
    
    def research(self, code: str, df: pd.DataFrame, realtime: Dict) -> Dict:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        price = realtime.get('price', close.iloc[-1])
        
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        
        bb_mid = close.rolling(20).mean().iloc[-1]
        bb_std = close.rolling(20).std().iloc[-1]
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        
        high20 = high.tail(20).max()
        low20 = low.tail(20).min()
        
        # 支撑位（从低到高排序）
        supports = []
        if low20 < price:
            supports.append(("20日低点", low20, 85))
        if ma60 < price:
            supports.append(("MA60", ma60, 80))
        if ma20 < price:
            supports.append(("MA20", ma20, 75))
        if ma5 < price:
            supports.append(("MA5", ma5, 70))
        supports.append(("布林下轨", bb_lower, 70))
        
        # 阻力位
        resistances = []
        if high20 > price:
            resistances.append(("20日高点", high20, 85))
        if ma5 > price:
            resistances.append(("MA5", ma5, 70))
        if ma20 > price:
            resistances.append(("MA20", ma20, 80))
        if bb_upper > price:
            resistances.append(("布林上轨", bb_upper, 75))
        
        supports.sort(key=lambda x: x[1])
        resistances.sort(key=lambda x: x[1], reverse=True)
        
        nearest_support = supports[0] if supports else (None, price * 0.95, 50)
        nearest_resistance = resistances[0] if resistances else (None, price * 1.05, 50)
        
        buy_point = nearest_support[1] if nearest_support[1] < price else price * 0.99
        stop_loss = nearest_support[1] * 0.97
        target = nearest_resistance[1] if nearest_resistance[1] > price else price * 1.08
        
        risk = abs(buy_point - stop_loss)
        reward = abs(target - buy_point)
        risk_ratio = reward / risk if risk > 0 else 1
        
        upside = (nearest_resistance[1] - price) / price * 100 if nearest_resistance[1] > price else 0
        
        score = 0
        if nearest_support[2] >= 80:
            score += 30
        elif nearest_support[2] >= 70:
            score += 20
        if upside > 10:
            score += 25
        elif upside > 5:
            score += 15
        if risk_ratio >= 2:
            score += 25
        elif risk_ratio >= 1.5:
            score += 15
        
        dist_to_support = (price - nearest_support[1]) / price * 100 if nearest_support[1] else 0
        if dist_to_support < 3:
            score += 20
        
        return {
            "当前价格": price,
            "最近支撑": f"{nearest_support[0]}({nearest_support[1]:.2f})",
            "支撑强度": nearest_support[2],
            "最近阻力": f"{nearest_resistance[0]}({nearest_resistance[1]:.2f})",
            "阻力强度": nearest_resistance[2],
            "建议买入点": round(buy_point, 2),
            "建议止损位": round(stop_loss, 2),
            "第一目标位": round(target, 2),
            "上涨空间": f"{upside:.1f}%",
            "风险回报比": f"1:{risk_ratio:.1f}",
            "操作建议": "回调买入" if dist_to_support > 1 else "突破买入",
            "战法评分": min(100, score),
            "置信度": "高" if score >= 70 else ("中" if score >= 50 else "低")
        }


class AgentPattern(BaseAgent):
    """形态专家"""
    
    def __init__(self):
        super().__init__("形态专家", "K线形态", "W底/杯柄/突破")
    
    def research(self, code: str, df: pd.DataFrame, realtime: Dict) -> Dict:
        close = df['close']
        high = df['high']
        low = df['low']
        price = realtime.get('price', close.iloc[-1])
        
        low_vals = low.tail(60)
        low_min1 = low_vals.min()
        low_idx1 = low_vals.argmin()
        
        after_first = low_vals.iloc[low_idx1:]
        if len(after_first) > 5:
            low_min2 = after_first.iloc[5:].min()
            low_idx2 = low_idx1 + after_first.iloc[5:].argmin() + 5
        else:
            low_min2 = low_min1
            low_idx2 = low_idx1
        
        w_score = 0
        w_point = None
        if low_idx1 != low_idx2:
            diff = abs(low_min1 - low_min2) / max(low_min1, low_min2)
            if diff < 0.10:
                w_score = 75
                w_point = (low_min1 + low_min2) / 2
        
        recent = close.tail(30)
        cup_high = recent.max()
        cup_low = recent.min()
        cup_mid = (cup_high + cup_low) / 2
        cup_score = 70 if close.iloc[-1] > cup_mid else 30
        
        recent_high = high.tail(20).max()
        breakout = price > recent_high * 0.98
        
        if len(close) >= 10:
            recent10 = close.tail(10)
            flag_range = recent10.max() - recent10.min()
            flag_pct = flag_range / recent10.mean() * 100
            flag_score = 65 if flag_pct < 8 else 30
        else:
            flag_score = 30
        
        recent5 = df.tail(5)
        yangxian_count = sum(recent5['close'] > recent5['open'])
        
        total = 0
        patterns = []
        if w_score >= 70:
            total += w_score
            patterns.append("W双底 ✅")
        if cup_score >= 70:
            total += cup_score - 10
            patterns.append("杯柄形态 ✅")
        if breakout:
            total += 25
            patterns.append("突破前高 ✅")
        if flag_score >= 65:
            total += flag_score - 15
            patterns.append("旗形整理 ✅")
        if yangxian_count >= 3:
            total += 15
            patterns.append(f"阳线{yangxian_count}/5 ✅")
        
        total = min(100, total)
        
        if w_score >= 70:
            buy_p = w_point * 1.02
            stop_l = w_point * 0.97
            target_p = recent_high
        elif breakout:
            buy_p = price
            stop_l = price * 0.97
            target_p = price * 1.10
        else:
            buy_p = price * 0.99
            stop_l = price * 0.95
            target_p = recent_high
        
        risk = abs(buy_p - stop_l)
        reward = abs(target_p - buy_p)
        rr = reward / risk if risk > 0 else 1
        
        return {
            "当前价格": price,
            "W双底": f"{w_point:.2f}" if w_point else "未形成",
            "W底评分": w_score,
            "杯柄形态": f"中点{cup_mid:.2f}" if cup_score >= 70 else "未形成",
            "杯柄评分": cup_score,
            "突破信号": "是 ✅" if breakout else "否",
            "旗形整理": "是 ✅" if flag_score >= 65 else "否",
            "建议买入点": round(buy_p, 2),
            "建议止损位": round(stop_l, 2),
            "目标位": round(target_p, 2),
            "风险回报比": f"1:{rr:.1f}",
            "形态信号": " | ".join(patterns) if patterns else "形态不明显",
            "战法评分": total,
            "置信度": "高" if total >= 70 else ("中" if total >= 50 else "低")
        }


class AgentMovingAverage(BaseAgent):
    """均线专家"""
    
    def __init__(self):
        super().__init__("均线专家", "均线战法", "2560+均线系统")
    
    def research(self, code: str, df: pd.DataFrame, realtime: Dict) -> Dict:
        close = df['close']
        volume = df['volume']
        price = realtime.get('price', close.iloc[-1])
        
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma25 = close.rolling(25).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ma60 = volume.rolling(60).mean().iloc[-1]
        
        ma25_prev = close.rolling(25).mean().iloc[-5]
        ma25_up = ma25 > ma25_prev
        
        vol_ma5_prev = volume.rolling(5).mean().iloc[-2]
        vol_ma60_prev = volume.rolling(60).mean().iloc[-2]
        vol_golden = vol_ma5_prev < vol_ma60_prev and vol_ma5 > vol_ma60
        
        score_2560 = 0
        if ma25_up:
            score_2560 += 50
        if vol_golden:
            score_2560 += 50
        
        ma_bullish = ma5 > ma10 > ma20
        ma_bearish = ma5 < ma10 < ma20
        
        ma5_above_10_prev = close.rolling(5).mean().iloc[-2] > close.rolling(10).mean().iloc[-2]
        ma5_above_10_now = ma5 > ma10
        golden_cross = ma5_above_10_now and not ma5_above_10_prev
        death_cross = not ma5_above_10_now and ma5_above_10_prev
        
        support_ma = None
        dist_to_support = 999
        if price > ma5:
            support_ma = "MA5"
            dist_to_support = (price - ma5) / price * 100
        elif price > ma10:
            support_ma = "MA10"
            dist_to_support = (price - ma10) / price * 100
        elif price > ma20:
            support_ma = "MA20"
            dist_to_support = (price - ma20) / price * 100
        
        total = 0
        signals = []
        if score_2560 >= 80:
            total += score_2560
            signals.append("2560买入信号 ✅")
        elif score_2560 >= 50:
            total += score_2560 * 0.6
            signals.append("2560部分信号 🟡")
        if ma_bullish:
            total += 25
            signals.append("均线多头 ✅")
        elif ma_bearish:
            total -= 20
            signals.append("均线空头 ⚠️")
        if golden_cross:
            total += 20
            signals.append("MA5上穿MA10金叉 ✅")
        if support_ma and dist_to_support < 2:
            total += 15
            signals.append(f"MA{support_ma}支撑 ✅")
        
        total = min(100, max(0, total))
        
        if total >= 70:
            buy_point = ma5 * 1.005 if ma_bullish else price
            stop_loss = ma20 * 0.98
        elif total >= 50:
            buy_point = price * 0.995
            stop_loss = price * 0.95
        else:
            buy_point = None
            stop_loss = price * 0.95
        
        target = price * 1.08 if total >= 50 else price * 1.05
        rr = 1.6 if total >= 70 else 1.2
        
        return {
            "当前价格": price,
            "MA5": round(ma5, 2),
            "MA10": round(ma10, 2),
            "MA20": round(ma20, 2),
            "MA25": round(ma25, 2),
            "MA60": round(ma60, 2),
            "MA25趋势": "向上 ✅" if ma25_up else "向下 ⚠️",
            "量能金叉": "是 ✅" if vol_golden else "否",
            "均线多头": "是 ✅" if ma_bullish else ("否 ⚠️" if ma_bearish else "混合 🟡"),
            "MA5/MA10状态": "金叉 ✅" if golden_cross else ("死叉 ⚠️" if death_cross else "纠缠"),
            "2560战法评分": score_2560,
            "建议买入点": round(buy_point, 2) if buy_point else "等待信号",
            "建议止损位": round(stop_loss, 2),
            "目标位": round(target, 2),
            "风险回报比": f"1:{rr:.1f}",
            "均线信号": " | ".join(signals) if signals else "暂无明确信号",
            "战法评分": total,
            "置信度": "高" if total >= 70 else ("中" if total >= 50 else "低")
        }


class AgentShortTerm(BaseAgent):
    """短线专家 - 尾盘+隔夜+换手率"""
    
    def __init__(self):
        super().__init__("短线专家", "短线战法", "尾盘买入+隔夜持股")
    
    def research(self, code: str, df: pd.DataFrame, realtime: Dict) -> Dict:
        close = df['close']
        open_p = df['open']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        price = realtime.get('price', close.iloc[-1])
        pct = realtime.get('pct', 0)
        today_high = realtime.get('high', high.iloc[-1])
        today_low = realtime.get('low', low.iloc[-1])
        
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
        
        avg_vol = volume.tail(20).mean()
        turnover = (volume.iloc[-1] / avg_vol - 1) * 100 if avg_vol > 0 else 0
        
        day_range = today_high - today_low
        intra_pos = (price - today_low) / day_range * 100 if day_range > 0 else 50
        
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma_bullish = ma5 > ma10
        
        pct_ok = 3 <= abs(pct) <= 7
        vol_ok = vol_ratio > 1.5
        turnover_ok = turnover > 3
        ma_ok = ma_bullish
        
        vol_trend = all(volume.iloc[-i] > volume.iloc[-i-1] for i in range(1, 4)) if len(volume) >= 4 else False
        
        body = price - open_p.iloc[-1]
        is_yang = body > 0
        upper_shadow = today_high - max(price, open_p.iloc[-1])
        is_whip = upper_shadow < body * 0.3 if body > 0 else True
        kline_good = is_yang and is_whip
        
        high20 = high.tail(20).max()
        break_high = price > high20 * 0.98
        
        passed = sum([pct_ok, vol_ok, turnover_ok, ma_ok, vol_trend, kline_good, break_high])
        
        total = 0
        signals = []
        if pct_ok:
            total += 15
            signals.append(f"涨幅{pct:.1f}% ✅")
        else:
            signals.append(f"涨幅{pct:.1f}% ❌")
        if vol_ok:
            total += 15
            signals.append(f"量比{vol_ratio:.2f} ✅")
        else:
            signals.append(f"量比{vol_ratio:.2f} ❌")
        if turnover_ok:
            total += 10
            signals.append(f"换手率{turnover:.1f}% ✅")
        if ma_ok:
            total += 20
            signals.append("均线多头 ✅")
        if vol_trend:
            total += 15
            signals.append("量能放大 ✅")
        if kline_good:
            total += 15
            signals.append("K线良好 ✅")
        if break_high:
            total += 10
            signals.append("突破前高 ✅")
        
        total = min(100, total)
        
        if passed >= 6:
            signal = "🟢 强烈建议"
            action = "满仓隔夜"
        elif passed >= 4:
            signal = "🟢 建议"
            action = "适当参与"
        elif passed >= 3:
            signal = "🟡 谨慎"
            action = "轻仓试探"
        else:
            signal = "❌ 不建议"
            action = "管住手"
        
        if total >= 70:
            buy_p = price
            stop_l = price * 0.97
            target_p = price * 1.08
        elif total >= 50:
            buy_p = price * 0.995
            stop_l = price * 0.95
            target_p = price * 1.05
        else:
            buy_p = None
            stop_l = price * 0.95
            target_p = price * 1.03
        
        rr = 1.5 if total >= 70 else 1.0
        
        return {
            "当前价格": price,
            "今日涨幅": f"{pct:.2f}%",
            "量比": round(vol_ratio, 2),
            "换手估算": f"{turnover:.1f}%",
            "日内位置": f"{intra_pos:.1f}%",
            "尾盘建议": signal,
            "通过条件": f"{passed}/7",
            "建议买入点": round(buy_p, 2) if buy_p else "等待",
            "建议止损位": round(stop_l, 2),
            "目标位": round(target_p, 2),
            "风险回报比": f"1:{rr:.1f}",
            "短线信号": " | ".join(signals),
            "战法评分": total,
            "置信度": "高" if total >= 70 else ("中" if total >= 50 else "低")
        }


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
            results[agent_name] = {'error': str(e), 'score': 0}
    
    return results


def extract_signal(report: Dict) -> str:
    if '建议买入点' in report:
        buy = report.get('建议买入点')
        if buy and isinstance(buy, (int, float)):
            return f"买入点: {buy:.2f}"
    if '缠论信号' in report and '✅' in str(report.get('缠论信号', '')):
        return str(report.get('缠论信号'))
    if '均线信号' in report and '✅' in str(report.get('均线信号', '')):
        return str(report.get('均线信号'))
    if '短线信号' in report:
        return str(report.get('短线信号'))[:30]
    return "信号待确认"
