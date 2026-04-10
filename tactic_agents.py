#!/usr/bin/env python3
"""
战术专家智能体层 - 四大经典战法专项智能体

每个智能体负责一个战法的深度分析，输出结构化报告，
供决策委员会最终决策。

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

# ==================== 基础战术智能体类 ====================
class BaseTacticAgent(ABC):
    """战术智能体基类"""
    
    def __init__(self, name: str, strategy_name: str):
        self.name = name
        self.strategy_name = strategy_name
        self.author = ""
        self.description = ""
        
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Dict:
        """执行战法分析"""
        pass
    
    def get_report(self, df: pd.DataFrame, stock_name: str, stock_code: str) -> str:
        """生成结构化报告"""
        result = self.analyze(df)
        return self._format_report(result, stock_name, stock_code)
    
    def _format_report(self, result: Dict, name: str, code: str) -> str:
        """格式化报告"""
        signal = result.get('signal', '⚪ 观望')
        score = result.get('score', 0)
        confidence = result.get('confidence', '低')
        
        return f"""
╔══════════════════════════════════════════════════════════════╗
║  🎯 {self.strategy_name} - {self.name}                    ║
╠══════════════════════════════════════════════════════════════╣
║  股票: {name}({code})                                         ║
║  战法: {self.strategy_name}                                    ║
║  ═══════════════════════════════════════════════════════════  ║
║  📊 战术评分: {score:>3}/100  |  置信度: {confidence:<4}                 ║
║  🎯 信号: {signal:<30}                    ║
║  ═══════════════════════════════════════════════════════════  ║
║  📋 核心指标:                                                ║
{self._format_indicators(result)}
║  ═══════════════════════════════════════════════════════════  ║
║  💡 操作建议: {result.get('advice', '暂无')[:30]:<30}    ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    def _format_indicators(self, result: Dict) -> str:
        """格式化指标输出"""
        lines = []
        for key, value in result.get('indicators', {}).items():
            if isinstance(value, float):
                lines.append(f"║  • {key}: {value:>10.2f}                                   ║")
            else:
                lines.append(f"║  • {key}: {str(value):<35}       ║")
        return '\n'.join(lines) if lines else "║  暂无指标数据                                                  ║"


# ==================== 战术智能体1: 2560战法专家 ====================
class Agent2560(BaseTacticAgent):
    """
    2560战法专家智能体
    
    创始人: 安德烈·昂格尔 (Andreas Enberg)
    战绩: 3个月账户翻40倍
    
    核心逻辑:
    - MA25(25日均线): 判断趋势方向
    - VOL_MA5(5日均量): 短期资金活跃度
    - VOL_MA60(60日均量): 中长期资金动向
    
    买入信号: MA25向上 + VOL_MA5上穿VOL_MA60(金叉)
    卖出信号: VOL_MA5下穿VOL_MA60(死叉) 或 MA25走平/向下
    """
    
    def __init__(self):
        super().__init__("2560战法专家", "2560 Tactical")
        self.author = "安德烈·昂格尔"
        self.description = "均线+量能共振战法"
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """执行2560战法分析"""
        close = df['close']
        volume = df['volume']
        
        # 计算核心指标
        ma25 = close.rolling(25).mean()
        vol_ma5 = volume.rolling(5).mean()
        vol_ma60 = volume.rolling(60).mean()
        
        current_ma25 = ma25.iloc[-1]
        prev_ma25 = ma25.iloc[-5]
        
        current_vol_ma5 = vol_ma5.iloc[-1]
        prev_vol_ma5 = vol_ma5.iloc[-2]
        current_vol_ma60 = vol_ma60.iloc[-1]
        prev_vol_ma60 = vol_ma60.iloc[-2]
        
        # MA25趋势分析
        ma25_trend = 'up' if current_ma25 > prev_ma25 else 'down'
        ma25_slope = (current_ma25 - prev_ma25) / prev_ma25 * 100
        
        # 量能金叉/死叉检测
        vol_golden_cross = prev_vol_ma5 < prev_vol_ma60 and current_vol_ma5 > current_vol_ma60
        vol_death_cross = prev_vol_ma5 > prev_vol_ma60 and current_vol_ma5 < current_vol_ma60
        
        # 价格位置
        price = close.iloc[-1]
        price_vs_ma25 = 'above' if price > current_ma25 else 'below'
        
        # 计算评分
        score = 0
        indicators = {}
        
        # MA25趋势 (40分)
        if ma25_trend == 'up':
            score += 40
            indicators['MA25趋势'] = '↑ 向上'
        else:
            indicators['MA25趋势'] = '↓ 向下'
        indicators['MA25斜率(%)'] = round(ma25_slope, 2)
        
        # 量能金叉 (40分)
        if vol_golden_cross:
            score += 40
            indicators['量能信号'] = '✅ 金叉买入'
        elif vol_death_cross:
            indicators['量能信号'] = '🔴 死叉卖出'
        else:
            indicators['量能信号'] = '➖ 无信号'
        
        # 价格在MA25上方 (20分)
        if price_vs_ma25 == 'above':
            score += 20
        indicators['价格vsMA25'] = '线上 ✅' if price_vs_ma25 == 'above' else '线下 ⚠️'
        
        # 确定信号
        if score >= 80 and vol_golden_cross:
            signal = "🟢 强烈买入"
            confidence = "高"
            advice = "MA25向上+量能金叉，重仓买入"
        elif score >= 60 and ma25_trend == 'up':
            signal = "🟢 建议买入"
            confidence = "中高"
            advice = "趋势向上，可轻仓试探"
        elif ma25_trend == 'down' or vol_death_cross:
            signal = "🔴 建议卖出"
            confidence = "高"
            advice = "趋势转弱，及时止损"
        else:
            signal = "⚪ 观望"
            confidence = "中"
            advice = "等待量能金叉确认"
        
        return {
            'score': min(100, score),
            'signal': signal,
            'confidence': confidence,
            'advice': advice,
            'ma25_trend': ma25_trend,
            'ma25_slope': ma25_slope,
            'vol_golden_cross': vol_golden_cross,
            'vol_death_cross': vol_death_cross,
            'indicators': indicators
        }


# ==================== 战术智能体2: 尾盘买入专家 ====================
class AgentClosingTime(BaseTacticAgent):
    """
    尾盘买入法专家智能体
    
    核心逻辑:
    - 尾盘(14:30-15:00)是多空决策关键窗口
    - 选取涨幅3%-5%的强势股
    - 量比>1.5，K线收阳
    - 次日开盘/早盘卖出
    
    选股条件:
    1. 涨幅3%-5%（最佳区间）
    2. 量比>1.5
    3. 股价在MA5上方
    4. K线收阳，上影线短
    """
    
    def __init__(self):
        super().__init__("尾盘买入专家", "Closing Time Tactical")
        self.description = "14:30尾盘强势股选股战术"
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """执行尾盘买入法分析"""
        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        price = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        # 涨幅分析
        pct_change = (price - prev_close) / prev_close * 100
        
        # 量比分析
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
        
        # MA5位置
        ma5 = close.rolling(5).mean().iloc[-1]
        above_ma5 = price > ma5
        
        # K线形态
        body = price - open_price.iloc[-1]
        body_pct = body / prev_close * 100
        upper_shadow = high.iloc[-1] - max(price, open_price.iloc[-1])
        lower_shadow = min(price, open_price.iloc[-1]) - low.iloc[-1]
        
        is_yangxian = body > 0
        is_whip = upper_shadow < body * 0.3 if body > 0 else False
        
        # 计算评分
        score = 0
        indicators = {}
        
        # 涨幅区间 (30分)
        if 3 <= pct_change <= 5:
            score += 30
            indicators['涨幅区间'] = '✅ 最佳区间(3-5%)'
        elif 2 <= abs(pct_change) < 3:
            score += 15
            indicators['涨幅区间'] = '🟡 偏低'
        elif 5 < pct_change <= 7:
            score += 10
            indicators['涨幅区间'] = '🔴 偏高(易追高)'
        else:
            indicators['涨幅区间'] = '❌ 超范围'
        
        indicators['今日涨幅(%)'] = round(pct_change, 2)
        
        # 量比 (25分)
        if vol_ratio > 1.5:
            score += 25
            indicators['量比'] = f'✅ {vol_ratio:.2f} 放量'
        elif vol_ratio > 1.0:
            score += 10
            indicators['量比'] = f'🟡 {vol_ratio:.2f} 正常'
        else:
            indicators['量比'] = f'❌ {vol_ratio:.2f} 缩量'
        
        # MA5位置 (20分)
        if above_ma5:
            score += 20
            indicators['MA5位置'] = '✅ 线上'
        else:
            indicators['MA5位置'] = '❌ 线下'
        indicators['MA5'] = round(ma5, 2)
        
        # K线形态 (25分)
        if is_yangxian and is_whip:
            score += 25
            indicators['K线形态'] = '✅ 阳线+上影短'
        elif is_yangxian:
            score += 15
            indicators['K线形态'] = '🟡 阳线'
        else:
            indicators['K线形态'] = '❌ 阴线'
        indicators['K线实体(%)'] = round(body_pct, 2)
        
        # 确定信号
        if score >= 80:
            signal = "🟢 强烈建议尾盘买入"
            confidence = "高"
            advice = "尾盘强势，次日高开概率大"
        elif score >= 60:
            signal = "🟢 建议尾盘买入"
            confidence = "中高"
            advice = "条件较好，可适当参与"
        elif score >= 40:
            signal = "🟡 谨慎观望"
            confidence = "中"
            advice = "条件不完全满足"
        else:
            signal = "❌ 不建议尾盘买入"
            confidence = "低"
            advice = "条件不满足，风险较高"
        
        return {
            'score': min(100, score),
            'signal': signal,
            'confidence': confidence,
            'advice': advice,
            'pct_change': pct_change,
            'vol_ratio': vol_ratio,
            'indicators': indicators
        }


# ==================== 战术智能体3: 筹码分布专家 ====================
class AgentChips(BaseTacticAgent):
    """
    筹码战法专家智能体
    
    核心逻辑:
    - 筹码分布反映持仓成本
    - 筹码密集区形成支撑/压力
    - 主力吸筹完成 = 拉升前奏
    
    选股逻辑:
    1. 筹码集中度>40%（主力控盘）
    2. 获利盘<20%（低位吸筹）
    3. 筹码峰在当前价格下方
    4. 套牢盘较重区域在高位
    """
    
    def __init__(self):
        super().__init__("筹码分布专家", "Chip Distribution Tactical")
        self.description = "筹码分布与主力行为分析"
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """执行筹码战法分析"""
        close = df['close']
        volume = df['volume']
        
        price = close.iloc[-1]
        
        # 估算筹码分布（简化模型）
        # 使用最近N天的价格分布模拟筹码
        recent_days = min(60, len(df))
        recent_close = close.tail(recent_days)
        recent_vol = volume.tail(recent_days)
        
        # 计算筹码集中度
        price_min = recent_close.min() * 0.9
        price_max = recent_close.max() * 1.1
        bins = 20
        price_range = np.linspace(price_min, price_max, bins)
        
        chip_dists = []
        for i in range(len(price_range) - 1):
            mask = (recent_close >= price_range[i]) & (recent_close < price_range[i+1])
            vol_sum = recent_vol[mask].sum()
            chip_dists.append({
                'price_low': price_range[i],
                'price_high': price_range[i+1],
                'volume': vol_sum
            })
        
        # 找出筹码峰
        max_vol_idx = max(range(len(chip_dists)), key=lambda x: chip_dists[x]['volume'])
        peak = chip_dists[max_vol_idx]
        
        # 筹码集中度（筹码峰成交量/总成交量）
        total_vol = sum(d['volume'] for d in chip_dists)
        concentration = peak['volume'] / total_vol * 100 if total_vol > 0 else 0
        
        # 获利盘估算
        winning_mask = recent_close > price * 0.97
        winning_vol = recent_vol[winning_mask].sum()
        winning_pct = winning_vol / total_vol * 100 if total_vol > 0 else 50
        
        # 套牢盘估算
        losing_pct = 100 - winning_pct
        
        # 筹码峰位置
        peak_mid = (peak['price_low'] + peak['price_high']) / 2
        if peak_mid < price * 0.95:
            peak_position = "当前价下方 ✅"
            position_signal = 20
        elif peak_mid < price * 1.05:
            peak_position = "当前价附近 ⚖️"
            position_signal = 0
        else:
            peak_position = "当前价上方 🔴"
            position_signal = -20
        
        # 计算评分
        score = 0
        indicators = {}
        
        # 筹码集中度 (40分)
        if concentration > 40:
            score += 40
            indicators['集中度'] = f'💎 高度集中({concentration:.1f}%)'
        elif concentration > 25:
            score += 25
            indicators['集中度'] = f'📊 适度集中({concentration:.1f}%)'
        else:
            indicators['集中度'] = f'⚠️ 分散({concentration:.1f}%)'
        
        # 获利盘分析 (40分)
        if 20 <= winning_pct <= 60:
            score += 40
            indicators['获利盘'] = f'✅ 适中({winning_pct:.1f}%)'
        elif winning_pct < 20:
            score += 50  # 低位吸筹，加分
            indicators['获利盘'] = f'💎 低位({winning_pct:.1f}%)'
        elif winning_pct > 80:
            score -= 20  # 高位派发，减分
            indicators['获利盘'] = f'⚠️ 高位派发({winning_pct:.1f}%)'
        else:
            indicators['获利盘'] = f'⚖️ ({winning_pct:.1f}%)'
        
        # 筹码峰位置 (20分)
        score += max(0, position_signal)
        indicators['筹码峰位置'] = peak_position
        indicators['筹码峰区间'] = f"{peak['price_low']:.0f}-{peak['price_high']:.0f}"
        
        # 确定信号
        if score >= 70 and concentration > 30:
            signal = "🟢 强烈建议买入"
            confidence = "高"
            advice = "筹码高度集中，主力控盘"
        elif score >= 50:
            signal = "🟡 建议关注"
            confidence = "中"
            advice = "筹码结构良好"
        elif winning_pct > 80:
            signal = "🔴 高位风险"
            confidence = "高"
            advice = "获利盘过重，谨慎追高"
        else:
            signal = "⚪ 观望"
            confidence = "中"
            advice = "筹码等待进一步集中"
        
        return {
            'score': max(0, min(100, score)),
            'signal': signal,
            'confidence': confidence,
            'advice': advice,
            'concentration': concentration,
            'winning_pct': winning_pct,
            'indicators': indicators
        }


# ==================== 战术智能体4: 隔夜持股专家 ====================
class AgentOvernight(BaseTacticAgent):
    """
    隔夜持股法专家智能体
    
    核心理念:
    - 尾盘买入(14:30-15:00)，次日早盘卖出(9:30-10:00)
    - 持股时间短，隔夜风险可控
    - 利用消息面和资金惯性获利
    
    8步筛选:
    1. 涨幅3%-7%
    2. 量比>1.5
    3. 换手率>3%
    4. 均线多头
    5. 量能持续放大
    6. K线形态良好
    7. 突破关键位置
    8. 板块龙头优先
    """
    
    def __init__(self):
        super().__init__("隔夜持股专家", "Overnight Holding Tactical")
        self.description = "短周期隔夜套利战术"
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """执行隔夜持股法分析"""
        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        price = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        # 1. 涨幅筛选
        pct = (price - prev_close) / prev_close * 100
        pct_ok = 3 <= abs(pct) <= 7
        
        # 2. 量比
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
        vol_ok = vol_ratio > 1.5
        
        # 3. 换手率估算
        turnover = volume.iloc[-1] / volume.mean() * 100 if volume.mean() > 0 else 0
        turnover_ok = turnover > 3
        
        # 4. 均线多头
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma_bullish = ma5 > ma10 > ma20
        
        # 5. 量能趋势（连续放量）
        vol_trend_up = all(volume.iloc[-i] > volume.iloc[-i-1] for i in range(1, 4))
        
        # 6. K线形态
        body = price - open_price.iloc[-1]
        is_yangxian = body > 0
        upper_shadow = high.iloc[-1] - max(price, open_price.iloc[-1])
        is_whip = upper_shadow < body * 0.3 if body > 0 else True
        kline_good = is_yangxian and is_whip
        
        # 7. 突破高点
        high_20 = high.tail(20).max()
        break_high = price > high_20 * 0.98
        
        # 8. 强势股
        is_strong = pct > 5 if pct > 0 else False
        
        # 计算评分
        score = 0
        indicators = {}
        
        # 各项条件评分
        if pct_ok:
            score += 15
            indicators['1.涨幅筛选'] = f'✅ {pct:.2f}%'
        else:
            indicators['1.涨幅筛选'] = f'❌ {pct:.2f}%'
        
        if vol_ok:
            score += 15
            indicators['2.量比'] = f'✅ {vol_ratio:.2f}'
        else:
            indicators['2.量比'] = f'❌ {vol_ratio:.2f}'
        
        if turnover_ok:
            score += 10
            indicators['3.换手率'] = f'✅ {turnover:.2f}%'
        else:
            indicators['3.换手率'] = f'❌ {turnover:.2f}%'
        
        if ma_bullish:
            score += 20
            indicators['4.均线多头'] = '✅'
        else:
            indicators['4.均线多头'] = '❌'
        
        if vol_trend_up:
            score += 15
            indicators['5.量能持续'] = '✅'
        else:
            indicators['5.量能持续'] = '❌'
        
        if kline_good:
            score += 15
            indicators['6.K线良好'] = '✅'
        else:
            indicators['6.K线良好'] = '❌'
        
        if break_high:
            score += 5
            indicators['7.突破高点'] = '✅'
        else:
            indicators['7.突破高点'] = '❌'
        
        if is_strong:
            score += 5
            indicators['8.强势股'] = '✅'
        else:
            indicators['8.强势股'] = '❌'
        
        # 确定信号
        passed = sum([pct_ok, vol_ok, turnover_ok, ma_bullish, vol_trend_up, kline_good])
        
        if passed >= 7:
            signal = "🟢 强烈建议隔夜"
            confidence = "极高"
            advice = "8步全过，明日高开概率极大"
        elif passed >= 5:
            signal = "🟢 建议隔夜"
            confidence = "高"
            advice = "条件较好，可适当参与"
        elif passed >= 3:
            signal = "🟡 谨慎隔夜"
            confidence = "中"
            advice = "部分条件满足，控制仓位"
        else:
            signal = "❌ 不建议隔夜"
            confidence = "低"
            advice = "条件不满足，风险较高"
        
        return {
            'score': min(100, score),
            'signal': signal,
            'confidence': confidence,
            'advice': advice,
            'passed_steps': f"{passed}/8",
            'indicators': indicators
        }


# ==================== 战术智能体工厂 ====================
class TacticAgentFactory:
    """战术智能体工厂"""
    
    _agents = {
        '2560': Agent2560(),
        'closing': AgentClosingTime(),
        'chips': AgentChips(),
        'overnight': AgentOvernight(),
    }
    
    @classmethod
    def get_agent(cls, tactic_type: str) -> Optional[BaseTacticAgent]:
        """获取指定类型的战术智能体"""
        return cls._agents.get(tactic_type)
    
    @classmethod
    def get_all_agents(cls) -> List[BaseTacticAgent]:
        """获取所有战术智能体"""
        return list(cls._agents.values())
    
    @classmethod
    def run_all(cls, df: pd.DataFrame, stock_name: str, stock_code: str) -> Dict:
        """运行所有战术智能体"""
        results = {}
        for name, agent in cls._agents.items():
            try:
                results[name] = {
                    'agent_name': agent.name,
                    'strategy': agent.strategy_name,
                    'result': agent.analyze(df),
                    'report': agent.get_report(df, stock_name, stock_code)
                }
            except Exception as e:
                results[name] = {
                    'agent_name': agent.name,
                    'error': str(e)
                }
        return results


# ==================== 战术汇总分析器 ====================
class TacticSummary:
    """战术汇总分析器 - 汇总所有战术智能体结果"""
    
    @staticmethod
    def summarize(tactic_results: Dict) -> Dict:
        """汇总战术分析结果"""
        scores = []
        signals = []
        
        for name, data in tactic_results.items():
            if 'error' in data:
                continue
            result = data.get('result', {})
            scores.append(result.get('score', 0))
            signals.append(result.get('signal', '⚪ 观望'))
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # 统计信号
        buy_count = sum(1 for s in signals if '🟢' in s)
        hold_count = sum(1 for s in signals if '🟡' in s)
        sell_count = sum(1 for s in signals if '🔴' in s)
        
        return {
            'avg_score': round(avg_score, 1),
            'scores': scores,
            'signals': signals,
            'buy_count': buy_count,
            'hold_count': hold_count,
            'sell_count': sell_count,
            'total': len(scores)
        }
    
    @staticmethod
    def get_final_signal(summary: Dict) -> str:
        """根据汇总确定最终信号"""
        buy = summary['buy_count']
        hold = summary['hold_count']
        sell = summary['sell_count']
        total = summary['total']
        avg = summary['avg_score']
        
        if buy >= 3:
            return "🟢 强烈买入 (战术共振)"
        elif buy >= 2 and avg >= 60:
            return "🟢 建议买入 (多战术支持)"
        elif hold >= 3:
            return "🟡 观望为主"
        elif buy >= 1 and avg >= 50:
            return "🟡 谨慎买入"
        elif sell >= 2:
            return "🔴 建议卖出"
        else:
            return "⚪ 方向不明"
    
    @staticmethod
    def print_tactic_report(tactic_results: Dict, stock_name: str, stock_code: str):
        """打印战术汇总报告"""
        print(f"\n{'='*65}")
        print(f"  🎯 战术专家智能体分析报告 - {stock_name}({stock_code})")
        print(f"{'='*65}")
        
        # 各战术详细结果
        for name, data in tactic_results.items():
            if 'error' in data:
                print(f"\n❌ {data['agent_name']}: {data['error']}")
                continue
            result = data.get('result', {})
            score = result.get('score', 0)
            signal = result.get('signal', '⚪ 观望')
            advice = result.get('advice', '')
            
            emoji = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴" if score >= 30 else "⚪")
            
            print(f"\n{emoji} {data['agent_name']}")
            print(f"   评分: {score:>3}/100 | 信号: {signal}")
            print(f"   建议: {advice}")
        
        # 汇总
        summary = TacticSummary.summarize(tactic_results)
        final_signal = TacticSummary.get_final_signal(summary)
        
        print(f"\n{'='*65}")
        print(f"  📊 战术评分汇总")
        print(f"{'='*65}")
        print(f"  平均评分: {summary['avg_score']:>5.1f}/100")
        print(f"  买入信号: {summary['buy_count']}  |  观望信号: {summary['hold_count']}  |  卖出信号: {summary['sell_count']}")
        print(f"")
        print(f"  🏛️ 最终战术信号: {final_signal}")
        print(f"{'='*65}\n")


# ==================== 测试 ====================
if __name__ == "__main__":
    import baostock as bs
    
    def get_stock_data(code, days=90):
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
        
        if len(data) < 30:
            return None
        
        df = pd.DataFrame(data, columns=rs.fields)
        for col in ['open','high','low','close','volume','pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna()
    
    # 测试
    print("\n" + "="*65)
    print("  🎯 战术专家智能体层 - 测试运行")
    print("="*65)
    
    code, name = "600519", "贵州茅台"
    df = get_stock_data(code, 90)
    
    if df is not None:
        # 运行所有战术智能体
        results = TacticAgentFactory.run_all(df, name, code)
        
        # 打印汇总报告
        TacticSummary.print_tactic_report(results, name, code)
    else:
        print("❌ 数据获取失败")
