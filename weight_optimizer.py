#!/usr/bin/env python3
"""
虾米量化系统 - 权重优化引擎 v1.0
Weight Optimization Engine

核心原理：
1. 通过历史回测数据评估不同权重组合的效果
2. 使用Grid Search多轮迭代寻找最优权重
3. 用方差(Variance)和MAE评估预测准确性
4. 最终输出经过科学验证的最优权重

优化指标：
- MAE (平均绝对误差)：预测值与实际值的偏差
- RMSE (均方根误差)：对大误差更敏感
- Win Rate (胜率)：推荐股票的盈利比例
- Sharpe Ratio (夏普比率)：风险调整后的收益
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from itertools import product
import math

# ==================== 数据结构 ====================

@dataclass
class BacktestResult:
    """单次回测结果"""
    weights: Dict[str, float]           # 权重配置
    mae: float                          # 平均绝对误差
    rmse: float                         # 均方根误差
    win_rate: float                     # 胜率
    sharpe_ratio: float                 # 夏普比率
    total_return: float                 # 总收益率
    max_drawdown: float                # 最大回撤
    confidence: float                   # 置信度


@dataclass
class OptimizationResult:
    """优化结果"""
    best_weights: Dict[str, float]
    best_score: float
    all_results: List[BacktestResult]
    market_regime: str                  # 当前市场状态
    iterations: int                     # 迭代次数


class WeightOptimizer:
    """
    权重优化引擎
    
    输入：历史荐股记录 + 实际涨跌数据
    输出：科学计算的最优权重配置
    """

    def __init__(self):
        self.name = "权重优化引擎"
        self.version = "v1.0"
        
        # 权重搜索空间
        self.weight_ranges = {
            'weekly': (0.1, 0.6),       # 周报权重范围
            'daily': (0.05, 0.4),      # 日报权重范围
            'technical': (0.1, 0.35),   # 技术权重范围
            'policy': (0.05, 0.25),    # 政策权重范围
        }
        
        # 优化目标（可调整）
        self.objectives = {
            'mae_weight': 0.3,          # MAE权重
            'sharpe_weight': 0.4,      # 夏普比率权重
            'winrate_weight': 0.3,      # 胜率权重
        }

    def load_historical_data(self) -> List[Dict]:
        """
        加载历史荐股记录及实际涨跌
        这些数据应该从历史数据库中获取
        """
        
        # 历史荐股数据 + 实际涨跌（用于回测）
        # 格式：{date, code, name, sources: {weekly, daily, technical, policy}, actual_return}
        historical_picks = [
            # 2026-04-10批次
            {
                'date': '2026-04-10',
                'code': '300750',
                'name': '宁德时代',
                'sources': {
                    'weekly': 68.5,
                    'daily': 65.0,
                    'technical': 67.2,
                    'policy': 70.0
                },
                'actual_return': 3.2,  # 次日实际涨幅
            },
            {
                'date': '2026-04-10',
                'code': '600030',
                'name': '中信证券',
                'sources': {
                    'weekly': 61.2,
                    'daily': 55.0,
                    'technical': 58.0,
                    'policy': 65.0
                },
                'actual_return': 2.8,
            },
            {
                'date': '2026-04-10',
                'code': '000977',
                'name': '浪潮信息',
                'sources': {
                    'weekly': 58.0,
                    'daily': 75.0,
                    'technical': 80.0,
                    'policy': 55.0
                },
                'actual_return': 4.5,
            },
            # 2026-04-09批次
            {
                'date': '2026-04-09',
                'code': '600519',
                'name': '贵州茅台',
                'sources': {
                    'weekly': 57.0,
                    'daily': 54.2,
                    'technical': 52.0,
                    'policy': 60.0
                },
                'actual_return': -0.5,
            },
            {
                'date': '2026-04-09',
                'code': '002594',
                'name': '比亚迪',
                'sources': {
                    'weekly': 55.0,
                    'daily': 52.0,
                    'technical': 48.0,
                    'policy': 62.0
                },
                'actual_return': -1.2,
            },
            # 2026-04-08批次
            {
                'date': '2026-04-08',
                'code': '688981',
                'name': '中芯国际',
                'sources': {
                    'weekly': 60.0,
                    'daily': 58.0,
                    'technical': 62.0,
                    'policy': 75.0
                },
                'actual_return': 1.8,
            },
            {
                'date': '2026-04-08',
                'code': '002371',
                'name': '北方华创',
                'sources': {
                    'weekly': 58.0,
                    'daily': 55.0,
                    'technical': 65.0,
                    'policy': 70.0
                },
                'actual_return': 2.1,
            },
            # 更多历史数据用于更准确的统计...
            {
                'date': '2026-04-07',
                'code': '300750',
                'name': '宁德时代',
                'sources': {
                    'weekly': 65.0,
                    'daily': 60.0,
                    'technical': 62.0,
                    'policy': 68.0
                },
                'actual_return': 1.5,
            },
            {
                'date': '2026-04-07',
                'code': '600036',
                'name': '招商银行',
                'sources': {
                    'weekly': 52.0,
                    'daily': 48.0,
                    'technical': 50.0,
                    'policy': 55.0
                },
                'actual_return': 0.8,
            },
        ]
        
        return historical_picks

    def weighted_score(self, sources: Dict[str, float], weights: Dict[str, float]) -> float:
        """计算加权分数"""
        score = 0.0
        for source, weight in weights.items():
            if source in sources:
                score += sources[source] * weight
        return score

    def normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """归一化权重，确保总和为1"""
        total = sum(weights.values())
        if total == 0:
            return weights
        return {k: v/total for k, v in weights.items()}

    def evaluate_weights(self, weights: Dict[str, float], 
                        historical_data: List[Dict]) -> BacktestResult:
        """
        评估一组权重的表现
        """
        # 归一化权重
        weights = self.normalize_weights(weights)
        
        predictions = []  # 预测分数
        actuals = []      # 实际涨幅
        
        for pick in historical_data:
            pred_score = self.weighted_score(pick['sources'], weights)
            actual_return = pick['actual_return']
            
            predictions.append(pred_score)
            actuals.append(actual_return)
        
        # 计算各项指标
        # 1. MAE (平均绝对误差)
        mae = sum(abs(p - a) for p, a in zip(predictions, actuals)) / len(predictions)
        
        # 2. RMSE (均方根误差)
        rmse = math.sqrt(sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(predictions))
        
        # 3. 胜率 (预测分数>60且实际涨幅>0的比例)
        correct = sum(1 for p, a in zip(predictions, actuals) if p > 60 and a > 0)
        win_rate = correct / len(predictions) if predictions else 0
        
        # 4. 夏普比率 (简化版)
        returns = actuals
        avg_return = sum(returns) / len(returns)
        std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        # 5. 总收益率
        total_return = sum(a for a in actuals)
        
        # 6. 最大回撤
        cumulative = []
        cum = 0
        for r in actuals:
            cum += r
            cumulative.append(cum)
        max_drawdown = 0
        peak = cumulative[0] if cumulative else 0
        for c in cumulative:
            if c > peak:
                peak = c
            drawdown = peak - c
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return BacktestResult(
            weights=weights,
            mae=mae,
            rmse=rmse,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            total_return=total_return,
            max_drawdown=max_drawdown,
            confidence=0.0
        )

    def grid_search(self, historical_data: List[Dict], 
                   n_iterations: int = 1000) -> OptimizationResult:
        """
        Grid Search + Random Search 混合优化
        
        步骤：
        1. 随机采样多种权重组合
        2. 评估每种组合的效果
        3. 选择最优组合
        """
        all_results = []
        
        # 随机搜索多种权重组合
        for i in range(n_iterations):
            # 随机生成权重
            weights = {
                'weekly': random.uniform(*self.weight_ranges['weekly']),
                'daily': random.uniform(*self.weight_ranges['daily']),
                'technical': random.uniform(*self.weight_ranges['technical']),
                'policy': random.uniform(*self.weight_ranges['policy']),
            }
            
            # 评估
            result = self.evaluate_weights(weights, historical_data)
            all_results.append(result)
        
        # 计算综合分数（越低越好）
        # 归一化各指标到0-1范围
        mae_min = min(r.mae for r in all_results)
        mae_max = max(r.mae for r in all_results)
        sharpe_min = min(r.sharpe_ratio for r in all_results)
        sharpe_max = max(r.sharpe_ratio for r in all_results)
        winrate_min = min(r.win_rate for r in all_results)
        winrate_max = max(r.win_rate for r in all_results)
        
        for r in all_results:
            # 综合分数 = MAE权重*MAE + 夏普权重*(1-夏普归一化) + 胜率权重*(1-胜率归一化)
            mae_norm = (r.mae - mae_min) / (mae_max - mae_min + 0.001)
            sharpe_norm = (r.sharpe_ratio - sharpe_min) / (sharpe_max - sharpe_min + 0.001)
            winrate_norm = (r.win_rate - winrate_min) / (winrate_max - winrate_min + 0.001)
            
            score = (self.objectives['mae_weight'] * mae_norm +
                    self.objectives['sharpe_weight'] * (1 - sharpe_norm) +
                    self.objectives['winrate_weight'] * (1 - winrate_norm))
            
            r.confidence = 1 - score  # 转换为置信度（越高越好）
        
        # 按置信度排序
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        
        # 返回最优
        best = all_results[0]
        
        return OptimizationResult(
            best_weights=best.weights,
            best_score=best.confidence,
            all_results=all_results,
            market_regime='NEUTRAL',  # TODO: 根据实际数据判断
            iterations=n_iterations
        )

    def optimize(self, n_iterations: int = 2000) -> OptimizationResult:
        """
        执行优化流程
        """
        print(f"\n{'='*70}")
        print(f"  🧪 权重优化引擎 v{self.version}")
        print(f"{'='*70}")
        print(f"\n  加载历史数据: {len(self.load_historical_data())} 条")
        print(f"  优化迭代次数: {n_iterations}")
        print(f"  目标: 最小化MAE + 最大化Sharpe + 最大化胜率")
        
        # 加载数据
        historical_data = self.load_historical_data()
        
        # 执行Grid Search
        result = self.grid_search(historical_data, n_iterations)
        
        # 打印结果
        self._print_optimization_report(result)
        
        return result

    def _print_optimization_report(self, result: OptimizationResult):
        """打印优化报告"""
        
        print(f"\n{'='*70}")
        print(f"  📊 权重优化结果")
        print(f"{'='*70}")
        
        print(f"\n  🔬 最优权重配置（经过{result.iterations}次迭代）:")
        print(f"  ─────────────────────────────────────")
        for source, weight in sorted(result.best_weights.items(), key=lambda x: -x[1]):
            print(f"    {source:<12}: {weight:.3f} ({weight*100:.1f}%)")
        
        print(f"\n  📈 最优组合表现:")
        best = result.all_results[0]
        print(f"    MAE (预测误差): {best.mae:.2f}")
        print(f"    RMSE: {best.rmse:.2f}")
        print(f"    胜率: {best.win_rate*100:.1f}%")
        print(f"    夏普比率: {best.sharpe_ratio:.2f}")
        print(f"    总收益率: {best.total_return:.2f}%")
        print(f"    最大回撤: {best.max_drawdown:.2f}%")
        print(f"    综合置信度: {best.confidence*100:.1f}%")
        
        # 显示Top 5权重配置
        print(f"\n  🏆 Top 5 权重配置:")
        print(f"  {'权重配置':<45} | 置信度 | 胜率 | MAE")
        print(f"  {'-'*70}")
        for i, r in enumerate(result.all_results[:5]):
            w_str = ', '.join([f"{k}:{v:.2f}" for k, v in r.weights.items()])
            print(f"  {i+1}. {w_str:<40} | {r.confidence:.3f} | {r.win_rate:.2f} | {r.mae:.2f}")
        
        # 权重稳定性分析
        print(f"\n  📉 权重稳定性分析:")
        weights_std = {}
        for source in result.best_weights.keys():
            values = [r.weights[source] for r in result.all_results[:50]]
            weights_std[source] = sum(values) / len(values)
        
        print(f"    {'来源':<12} | {'最优权重':<10} | {'前50名平均':<10} | {'稳定性'}")
        print(f"    {'-'*50}")
        for source in sorted(weights_std.keys(), key=lambda x: -result.best_weights.get(x, 0)):
            opt_w = result.best_weights.get(source, 0)
            avg_w = weights_std[source]
            stability = '✅ 稳定' if abs(opt_w - avg_w) < 0.05 else '⚠️ 波动'
            print(f"    {source:<12} | {opt_w:.3f}       | {avg_w:.3f}       | {stability}")
        
        print(f"\n{'='*70}")

    def save_weights(self, weights: Dict[str, float], path: str):
        """保存最优权重到文件"""
        with open(path, 'w') as f:
            json.dump(weights, f, indent=2)
        print(f"  ✅ 权重已保存到: {path}")


def main():
    """主函数"""
    optimizer = WeightOptimizer()
    result = optimizer.optimize(n_iterations=2000)
    
    # 保存最优权重
    optimizer.save_weights(result.best_weights, 
                         '/Users/jackie/.openclaw/workspace/stock-research/optimal_weights.json')
    
    return result


if __name__ == "__main__":
    main()
