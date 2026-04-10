#!/usr/bin/env python3
"""
虾米量化系统 - 动态权重决策引擎 v1.0
Dynamic Weight Decision Engine

核心原理：
1. 基于历史回测数据，使用Grid Search找到最优基础权重
2. 根据市场状态（牛市/熊市/震荡）动态调整权重
3. 定期重新优化权重（每周/每月）
4. 使用置信区间量化预测可靠性

市场状态识别：
- 牛市：动量指标强，风险偏好高 → 技术权重↑
- 熊市：防御为主，价值权重↑
- 震荡：均值回归，趋势权重↑
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# ==================== 动态权重引擎 ====================

@dataclass
class MarketRegime:
    """市场状态"""
    name: str                    # BULL/BEAR/NEUTRAL
    confidence: float            # 置信度 0-1
    indicators: Dict[str, float] # 判定指标


@dataclass
class DynamicWeights:
    """动态权重"""
    base_weights: Dict[str, float]    # 基础权重
    adjusted_weights: Dict[str, float] # 调整后权重
    market_regime: MarketRegime        # 当前市场状态
    confidence: float                  # 整体置信度
    source: str                        # weights/optimized/manual


class DynamicWeightEngine:
    """
    动态权重决策引擎
    """

    def __init__(self):
        self.name = "动态权重引擎"
        self.version = "v1.0"
        
        # 市场状态调整因子
        self.regime_adjustments = {
            'BULL': {   # 牛市：动量和技术更有效
                'weekly': 0.95,      # 周报维持高权重
                'technical': 1.20,  # 技术指标上调20%
                'daily': 1.10,      # 日报小幅上调
                'policy': 0.90,     # 政策权重下调
            },
            'BEAR': {   # 熊市：价值和防御为主
                'weekly': 1.10,      # 周报更加重要
                'technical': 0.80,  # 技术指标下调
                'daily': 0.70,      # 日报权重降低
                'policy': 1.30,     # 政策权重上调（防御）
            },
            'NEUTRAL': { # 震荡：均衡配置
                'weekly': 1.00,
                'technical': 1.00,
                'daily': 1.00,
                'policy': 1.00,
            }
        }
        
        # 当前基础权重（从优化结果或手动设置）
        self.base_weights = None

    def load_optimal_weights(self, path: str) -> Optional[Dict[str, float]]:
        """加载优化后的权重"""
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    weights = json.load(f)
                    print(f"  ✅ 加载优化权重: {path}")
                    return weights
        except Exception as e:
            print(f"  ⚠️ 加载失败: {e}")
        return None

    def detect_market_regime(self, index_code: str = '000001') -> MarketRegime:
        """
        识别当前市场状态
        
        指标：
        - MA5/MA20/MA60 趋势
        - RSI
        - 成交量趋势
        - 波动率
        """
        # TODO: 接入真实数据
        # 目前使用简化逻辑
        
        # 模拟数据
        indicators = {
            'ma5_slope': 0.5,      # MA5斜率
            'ma20_slope': 0.3,     # MA20斜率
            'rsi': 55.0,           # RSI
            'volume_trend': 0.2,    # 成交量趋势
            'volatility': 0.15,    # 波动率
        }
        
        # 判定逻辑
        score = 0
        if indicators['ma5_slope'] > 0.3:
            score += 1
        if indicators['rsi'] > 55:
            score += 1
        if indicators['volume_trend'] > 0:
            score += 1
        if indicators['volatility'] > 0.2:
            score -= 1
        
        if score >= 2:
            name = 'BULL'
            confidence = min(0.9, 0.5 + score * 0.1)
        elif score <= -1:
            name = 'BEAR'
            confidence = min(0.9, 0.5 + abs(score) * 0.1)
        else:
            name = 'NEUTRAL'
            confidence = 0.6
        
        return MarketRegime(name=name, confidence=confidence, indicators=indicators)

    def adjust_weights(self, base_weights: Dict[str, float],
                      regime: MarketRegime) -> Tuple[Dict[str, float], float]:
        """
        根据市场状态调整权重
        """
        adjustments = self.regime_adjustments.get(regime.name, 
                                                  self.regime_adjustments['NEUTRAL'])
        
        adjusted = {}
        for source, weight in base_weights.items():
            adj_factor = adjustments.get(source, 1.0)
            adjusted[source] = weight * adj_factor
        
        # 归一化
        total = sum(adjusted.values())
        adjusted = {k: v/total for k, v in adjusted.items()}
        
        # 置信度 = 基础置信度 * 市场状态置信度
        confidence = 0.7 * regime.confidence
        
        return adjusted, confidence

    def get_weights(self, 
                   use_optimized: bool = True,
                   weights_path: str = '/Users/jackie/.openclaw/workspace/stock-research/optimal_weights.json'
                   ) -> DynamicWeights:
        """
        获取当前动态权重
        """
        
        print(f"\n{'='*70}")
        print(f"  ⚙️  动态权重决策引擎 v{self.version}")
        print(f"{'='*70}")
        
        # 1. 获取基础权重
        if use_optimized:
            self.base_weights = self.load_optimal_weights(weights_path)
        
        if self.base_weights is None:
            # 默认权重（当没有优化数据时）
            self.base_weights = {
                'weekly': 0.40,
                'daily': 0.25,
                'technical': 0.20,
                'policy': 0.15,
            }
            print(f"  ⚠️ 使用默认权重（无优化数据）")
        
        print(f"\n  📌 基础权重:")
        for k, v in sorted(self.base_weights.items(), key=lambda x: -x[1]):
            print(f"     {k:<12}: {v:.3f} ({v*100:.1f}%)")
        
        # 2. 检测市场状态
        regime = self.detect_market_regime()
        print(f"\n  📊 市场状态: {regime.name}")
        print(f"     置信度: {regime.confidence:.1%}")
        print(f"     指标: RSI={regime.indicators['rsi']:.1f}, MA5斜率={regime.indicators['ma5_slope']:.2f}")
        
        # 3. 调整权重
        adjusted, confidence = self.adjust_weights(self.base_weights, regime)
        
        print(f"\n  📈 调整后权重 (×{regime.name}调整因子):")
        for k, v in sorted(adjusted.items(), key=lambda x: -x[1]):
            factor = self.regime_adjustments[regime.name].get(k, 1.0)
            arrow = '↑' if factor > 1 else ('↓' if factor < 1 else '→')
            print(f"     {k:<12}: {v:.3f} ({v*100:.1f}%) {arrow}{abs(factor-1)*100:.0f}%")
        
        print(f"\n  🎯 整体置信度: {confidence:.1%}")
        
        print(f"\n{'='*70}")
        
        return DynamicWeights(
            base_weights=self.base_weights,
            adjusted_weights=adjusted,
            market_regime=regime,
            confidence=confidence,
            source='optimized' if use_optimized else 'manual'
        )

    def print_weight_summary(self, dw: DynamicWeights):
        """打印权重摘要"""
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  🏛️  动态权重配置 - {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════════════╣
║  市场状态: {dw.market_regime.name} (置信度: {dw.market_regime.confidence:.1%})
║  权重来源: {dw.source}
║  整体置信度: {dw.confidence:.1%}
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  权重配置:                                                            ║
║  ─────────────────────────────────────────────────────────────────  ║""")
        
        for source, weight in sorted(dw.adjusted_weights.items(), key=lambda x: -x[1]):
            bar = '█' * int(weight * 40)
            print(f"║  {source:<12}: {weight:>5.1%} |{bar:<40}|")
        
        print(f"""║                                                                      ║
║  💡 权重说明:                                                          ║
║  • 周报(weekly): 深度研究，数据更新慢但可靠度高                          ║
║  • 日报(daily): 盘中验证，反映短期情绪变化                               ║
║  • 技术(technical): 量化指标，趋势择时                                 ║
║  • 政策(policy): 宏观风险，防御性调整                                  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
        """)


def main():
    """主函数"""
    engine = DynamicWeightEngine()
    dw = engine.get_weights(use_optimized=True)
    engine.print_weight_summary(dw)
    
    return dw


if __name__ == "__main__":
    main()
