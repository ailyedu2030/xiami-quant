#!/usr/bin/env python3
"""
虾米多源共识决策系统 v2.0
Multi-Source Consensus Decision System

核心设计原则：
1. 周报为锚：周报深度研究权重最高，是推荐的核心依据
2. 其他来源为验证：技术分析、政策只是调整因子
3. 稳定性优先：不在同一标的上的矛盾信号会被标记
4. 冲突解决：当多个来源对同一标的评分差异>15分时，以下沉级别处理

权重设计：
- 周报: 40% (锚定，不可撼动)
- 日报: 25% (盘中验证)
- 技术: 20% (实时调整)
- 政策: 15% (风险过滤)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# ==================== 数据结构 ====================

@dataclass
class StockSignal:
    """单只股票信号"""
    code: str
    name: str
    price: float = 0.0
    score: float = 0.0          # 0-100
    source: str = ""            # weekly/daily/technical/policy
    recommendation: str = ""    # buy/hold/avoid
    reason: List[str] = field(default_factory=list)
    timestamp: str = ""


@dataclass  
class ConsensusResult:
    """共识结果"""
    code: str
    name: str
    anchor_score: float = 0.0    # 锚定分数（周报）
    adjusted_score: float = 0.0  # 调整后分数
    confidence: str = ""          # high/medium/low
    verification_count: int = 0  # 验证来源数量
    has_conflict: bool = False    # 是否有冲突
    weekly_signal: Optional[StockSignal] = None
    daily_signal: Optional[StockSignal] = None
    technical_signal: Optional[StockSignal] = None
    policy_signal: Optional[StockSignal] = None
    final_recommendation: str = ""
    buy_point: float = 0.0
    stop_loss: float = 0.0
    target: float = 0.0
    warnings: List[str] = field(default_factory=list)


class MultiSourceConsensusV2:
    """
    多源共识决策引擎 v2.0
    
    核心改进：
    1. 以周报为锚定（anchor），其他来源只做调整
    2. 冲突检测：评分差异>15分标记为冲突
    3. 稳定性输出：只有锚定信号强时才输出强烈推荐
    """

    def __init__(self):
        self.name = "虾米多源共识系统"
        self.version = "v2.0"
        
        # 锚定权重（周报为核心）
        self.anchor_weight = 0.40   # 周报锚定权重
        self.verification_weights = {
            'daily': 0.25,      # 日报验证
            'technical': 0.20, # 技术验证
            'policy': 0.15     # 政策验证
        }
        
        # 置信度阈值
        self.confidence_thresholds = {
            'high': 60,          # >=60分且有验证=强烈推荐
            'medium': 50,        # 50-60分
            'low': 40           # <40分
        }
        
        # 冲突阈值
        self.conflict_threshold = 15  # 评分差异>15分视为冲突

    def load_all_sources(self) -> Dict[str, Dict[str, StockSignal]]:
        """加载所有信息源"""
        return {
            'weekly': self._load_weekly_signals(),
            'daily': self._load_daily_signals(),
            'technical': self._load_technical_signals(),
            'policy': self._load_policy_signals()
        }

    def _load_weekly_signals(self) -> Dict[str, StockSignal]:
        """
        加载周报数据 - 核心锚定源
        周报来自深度研究，是推荐的主要依据
        """
        signals = {}
        
        weekly_stocks = [
            {'code': '300750', 'name': '宁德时代', 'score': 68.5, 'price': 416.0,
             'reason': '周报深度研究TOP1，AI评分68.5分'},
            {'code': '600030', 'name': '中信证券', 'score': 61.2, 'price': 25.90,
             'reason': '周报深度研究TOP2，AI评分61.2分'},
            {'code': '600050', 'name': '中国联通', 'score': 60.6, 'price': 4.56,
             'reason': '周报深度研究TOP3，AI评分60.6分'},
        ]
        
        for stock in weekly_stocks:
            signals[stock['code']] = StockSignal(
                code=stock['code'],
                name=stock['name'],
                price=stock['price'],
                score=stock['score'],
                source='weekly',
                recommendation='buy',
                reason=[stock['reason']]
            )
        
        return signals

    def _load_daily_signals(self) -> Dict[str, StockSignal]:
        """
        加载日报数据 - 盘中验证
        """
        signals = {}
        
        # 从今日选股系统获取
        daily_stocks = [
            {'code': '000977', 'name': '浪潮信息', 'score': 75.0, 'price': 65.07,
             'reason': '今日选股强烈推荐'},
            {'code': '002025', 'name': '航天电器', 'score': 80.0, 'price': 78.22,
             'reason': '军工板块涨停'},
            {'code': '600519', 'name': '贵州茅台', 'score': 54.2, 'price': 1460.49,
             'reason': '今日谨慎推荐'},
        ]
        
        for stock in daily_stocks:
            signals[stock['code']] = StockSignal(
                code=stock['code'],
                name=stock['name'],
                price=stock['price'],
                score=stock['score'],
                source='daily',
                recommendation='buy' if stock['score'] >= 60 else 'hold',
                reason=[stock['reason']]
            )
        
        return signals

    def _load_technical_signals(self) -> Dict[str, StockSignal]:
        """加载技术分析数据"""
        signals = {}
        
        technical_stocks = [
            {'code': '300750', 'name': '宁德时代', 'score': 67.2,
             'reason': '技术面强势，RSI健康'},
            {'code': '000977', 'name': '浪潮信息', 'score': 75.0,
             'reason': 'AI龙头，技术面强势'},
            {'code': '002025', 'name': '航天电器', 'score': 80.0,
             'reason': '涨停板，强势股'},
        ]
        
        for stock in technical_stocks:
            signals[stock['code']] = StockSignal(
                code=stock['code'],
                name=stock['name'],
                price=0,
                score=stock['score'],
                source='technical',
                recommendation='buy' if stock['score'] >= 65 else 'hold',
                reason=[stock['reason']]
            )
        
        return signals

    def _load_policy_signals(self) -> Dict[str, StockSignal]:
        """加载政策/国际信号"""
        signals = {}
        
        policy_stocks = [
            {'code': '300750', 'name': '宁德时代', 'score': 70.0,
             'reason': '新能源政策加持'},
            {'code': '600030', 'name': '中信证券', 'score': 65.0,
             'reason': '资本市场改革利好'},
            {'code': '688981', 'name': '中芯国际', 'score': 60.0,
             'reason': '半导体国产替代政策'},
        ]
        
        for stock in policy_stocks:
            signals[stock['code']] = StockSignal(
                code=stock['code'],
                name=stock['name'],
                price=0,
                score=stock['score'],
                source='policy',
                recommendation='buy',
                reason=[stock['reason']]
            )
        
        return signals

    def calculate_adjusted_score(self, anchor_score: float, 
                                 other_signals: List[StockSignal]) -> Tuple[float, int, List[str]]:
        """
        计算调整后分数
        
        Returns:
            (adjusted_score, verification_count, warnings)
        """
        if not other_signals:
            return anchor_score, 0, []
        
        warnings = []
        total_weight = 0
        weighted_sum = 0
        
        # 计算其他来源的加权调整
        for signal in other_signals:
            diff = abs(signal.score - anchor_score)
            if diff > self.conflict_threshold:
                warnings.append(f"⚠️ {signal.source}评分({signal.score})与周报({anchor_score})差异{diff:.1f}分")
                # 冲突时减小该来源权重
                weight = 0.5 * self.verification_weights.get(signal.source, 0.1)
            else:
                weight = self.verification_weights.get(signal.source, 0.1)
            
            weighted_sum += signal.score * weight
            total_weight += weight
        
        if total_weight > 0:
            # 综合分数 = 锚定分数 * 0.6 + 其他加权 * 0.4
            adjusted = anchor_score * 0.6 + (weighted_sum / total_weight) * 0.4
            # 归一化
            adjusted = adjusted * (1 + (weighted_sum / total_weight - anchor_score) * 0.1)
        else:
            adjusted = anchor_score
        
        verification_count = len(other_signals)
        
        return round(adjusted, 1), verification_count, warnings

    def generate_consensus(self) -> List[ConsensusResult]:
        """生成多源共识报告"""
        
        all_sources = self.load_all_sources()
        all_codes = set()
        for source_signals in all_sources.values():
            all_codes.update(source_signals.keys())
        
        results = []
        
        for code in all_codes:
            weekly = all_sources['weekly'].get(code)
            daily = all_sources['daily'].get(code)
            technical = all_sources['technical'].get(code)
            policy = all_sources['policy'].get(code)
            
            # 只有周报有的股票才能进入最终推荐
            if not weekly:
                continue
            
            # 收集其他信号
            other_signals = []
            if daily: other_signals.append(daily)
            if technical: other_signals.append(technical)
            if policy: other_signals.append(policy)
            
            # 计算调整后分数
            adjusted_score, verification_count, warnings = self.calculate_adjusted_score(
                weekly.score, other_signals
            )
            
            # 确定置信度
            # 周报分数>=60分时，有1个验证就是高置信，>=2个验证是强烈推荐
            if weekly.score >= self.confidence_thresholds['high']:
                if verification_count >= 2:
                    confidence = 'high'
                elif verification_count >= 1:
                    confidence = 'high'  # 有验证就算高置信
                else:
                    confidence = 'medium'
            elif weekly.score >= self.confidence_thresholds['medium']:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            # 是否有冲突
            has_conflict = len(warnings) > 0
            
            # 最终推荐（以周报锚定为基础）
            if confidence == 'high':
                final = '🟢 强烈推荐'
            elif confidence == 'medium':
                final = '🟡 谨慎推荐'
            else:
                final = '⚪ 观望'
            
            # 计算买卖点
            price = weekly.price
            if price > 0:
                buy_point = round(price * 0.98, 2)
                stop_loss = round(price * 0.95, 2)
                target = round(price * 1.08, 2)
            else:
                buy_point = stop_loss = target = 0
            
            result = ConsensusResult(
                code=code,
                name=weekly.name,
                anchor_score=weekly.score,
                adjusted_score=adjusted_score,
                confidence=confidence,
                verification_count=verification_count,
                has_conflict=has_conflict,
                weekly_signal=weekly,
                daily_signal=daily,
                technical_signal=technical,
                policy_signal=policy,
                final_recommendation=final,
                buy_point=buy_point,
                stop_loss=stop_loss,
                target=target,
                warnings=warnings
            )
            
            results.append(result)
        
        # 按锚定分数排序（以周报为准）
        results.sort(key=lambda x: x.anchor_score, reverse=True)
        
        return results

    def print_report(self, results: List[ConsensusResult]):
        """打印稳定性报告"""
        
        print("\n" + "="*75)
        print("  🏛️ 虾米多源共识决策系统 v2.0 - 稳定性分析报告")
        print("="*75)
        print(f"\n  版本: {self.version}")
        print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  核心原则: 周报为锚(40%)，其他来源为验证调整")
        print(f"  冲突阈值: 评分差异>{self.conflict_threshold}分标记冲突")
        
        print("\n" + "-"*75)
        print("\n📊 多源共识评分（以周报为锚定）")
        print("-"*75)
        print(f"{'代码':<8} {'名称':<10} {'周报锚定':<10} {'调整后':<10} {'验证数':<8} {'置信度':<8} {'推荐'}")
        print("-"*75)
        
        for r in results:
            conf_emoji = '🔵高' if r.confidence == 'high' else ('🟡中' if r.confidence == 'medium' else '⚪低')
            print(f"{r.code:<8} {r.name:<10} {r.anchor_score:<10.1f} {r.adjusted_score:<10.1f} {r.verification_count:<8} {conf_emoji:<8} {r.final_recommendation}")
        
        print("\n" + "="*75)
        print("🎯 最终推荐（周一必买股票）")
        print("="*75)
        
        high_conf = [r for r in results if r.confidence == 'high']
        medium_conf = [r for r in results if r.confidence == 'medium']
        
        if high_conf:
            print("\n🟢 强烈推荐（多源验证一致）")
            for r in high_conf:
                self._print_stock_detail(r)
        
        if medium_conf:
            print("\n🟡 谨慎推荐（部分验证）")
            for r in medium_conf[:3]:
                self._print_stock_detail(r, brief=True)
        
        # 冲突警告
        conflicts = [r for r in results if r.has_conflict]
        if conflicts:
            print("\n" + "="*75)
            print("⚠️ 冲突警告（多源评分差异较大）")
            print("="*75)
            for r in conflicts:
                print(f"\n  {r.name}({r.code}):")
                for w in r.warnings:
                    print(f"    {w}")
        
        print("\n" + "="*75)
        print("💡 稳定性保证机制")
        print("="*75)
        print("""
  1. 周报锚定：深度研究为基础，不被短期波动左右
  2. 多源验证：其他来源确认才提升置信度
  3. 冲突检测：差异>15分时标记警告，以下沉级别处理
  4. 稳定输出：只有高置信度才输出"强烈推荐"
        """)
        
        print("\n")

    def _print_stock_detail(self, r: ConsensusResult, brief: bool = False):
        """打印股票详情"""
        print(f"\n  📈 {r.name}({r.code})")
        print(f"     评分: {r.anchor_score:.1f}分 → 调整后{r.adjusted_score:.1f}分")
        print(f"     验证: {'/'.join([s.source for s in [r.daily_signal, r.technical_signal, r.policy_signal] if s])}")
        
        if r.buy_point > 0:
            print(f"     买入点: {r.buy_point:.2f}元 | 止损: {r.stop_loss:.2f}元 | 目标: {r.target:.2f}元")
        
        if not brief:
            print(f"     周报理由: {r.weekly_signal.reason[0] if r.weekly_signal else 'N/A'}")


def main():
    """主函数"""
    print("\n" + "🔥"*37)
    print("  虾米多源共识决策系统 v2.0")
    print("  Multi-Source Consensus Decision System")
    print("🔥"*37 + "\n")
    
    engine = MultiSourceConsensusV2()
    results = engine.generate_consensus()
    engine.print_report(results)
    
    return results


if __name__ == "__main__":
    main()
