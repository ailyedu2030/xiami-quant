#!/usr/bin/env python3
"""
虾米量化系统 - 自适应多轮权重优化引擎
Adaptive Multi-Round Weight Optimization Engine

核心思想:
1. 多轮迭代优化 - 不断提高精度
2. 一切皆动态 - 没有固定权重
3. 事件驱动 - 政策/新闻/情绪实时影响权重
4. 时间衰减 - 近期的数据更重要
5. 市场状态感知 - 牛熊市不同策略

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import os

# ==================== 配置 ====================

@dataclass
class OptimizationConfig:
    """优化配置"""
    max_iterations: int = 100          # 最大迭代次数
    convergence_threshold: float = 0.001  # 收敛阈值
    learning_rate: float = 0.1          # 学习率
    regularization: float = 0.01        # 正则化防止过拟合
    lookback_days: int = 60             # 历史数据窗口
    time_decay_factor: float = 0.95     # 时间衰减因子
    confidence_level: float = 0.95      # 置信水平

# ==================== Agent性能跟踪 ====================

@dataclass
class AgentPerformance:
    """Agent性能跟踪"""
    name: str
    signals: List[int] = field(default_factory=list)  # 1=BUY, 0=HOLD, -1=AVOID
    actual_returns: List[float] = field(default_factory=list)  # 实际收益
    timestamps: List[str] = field(default_factory=list)  # 时间戳
    
    def add_record(self, signal: int, actual_return: float, timestamp: str):
        self.signals.append(signal)
        self.actual_returns.append(actual_return)
        self.timestamps.append(timestamp)
    
    def get_weighted_stats(self, decay: float = 0.95) -> Dict:
        """获取加权统计 (近期更重要)"""
        n = len(self.signals)
        if n < 5:
            return self._default_stats()
        
        # 时间衰减权重
        weights = np.array([decay ** (n - 1 - i) for i in range(n)])
        weights = weights / weights.sum()
        
        # 加权收益
        returns = np.array(self.actual_returns)
        weighted_return = np.sum(weights * returns)
        
        # 加权胜率
        wins = np.array([1 if r > 0 else 0 for r in self.actual_returns])
        weighted_win_rate = np.sum(weights * wins)
        
        # 加权波动率
        weighted_std = np.sqrt(np.sum(weights * (returns - weighted_return) ** 2))
        
        # 夏普比率
        sharpe = weighted_return / weighted_std if weighted_std > 0 else 0
        
        # 信息系数 (IC) - 信号与收益的相关性
        if len(self.signals) > 5:
            signal_array = np.array(self.signals)
            ic = np.corrcoef(signal_array, returns)[0, 1]
            if np.isnan(ic):
                ic = 0
        else:
            ic = 0
        
        return {
            'weighted_return': weighted_return,
            'weighted_win_rate': weighted_win_rate,
            'weighted_std': weighted_std,
            'sharpe_ratio': sharpe,
            'information_coefficient': ic,
            'sample_size': n
        }
    
    def _default_stats(self) -> Dict:
        return {
            'weighted_return': 0.0,
            'weighted_win_rate': 0.5,
            'weighted_std': 1.0,
            'sharpe_ratio': 0.0,
            'information_coefficient': 0.0,
            'sample_size': 0
        }

# ==================== 事件影响矩阵 ====================

class EventImpactMatrix:
    """
    事件影响矩阵
    不同类型的事件对不同Agent产生不同的影响权重
    """
    
    def __init__(self):
        # 基础影响矩阵 [政策, 新闻, 技术, 情绪, 市场]
        # 每个事件类型对Agent权重的影响系数
        self.base_matrix = {
            'policy': {
                'TechnicalAgent': 0.8,    # 政策对技术面影响减弱
                'TacticAgent': 0.6,       # 战术影响中等
                'RiskAgent': 1.2,         # 政策风险加大
                'NewsAgent': 1.5,         # 政策=新闻密集期
                'SectorAgent': 1.8         # 政策直接改变板块
            },
            'news': {
                'TechnicalAgent': 0.7,
                'TacticAgent': 0.8,
                'RiskAgent': 1.0,
                'NewsAgent': 1.8,         # 新闻Agent权重飙升
                'SectorAgent': 1.3
            },
            'technical': {
                'TechnicalAgent': 1.5,    # 技术信号主导
                'TacticAgent': 1.2,
                'RiskAgent': 0.8,
                'NewsAgent': 0.5,
                'SectorAgent': 0.6
            },
            'sentiment': {
                'TechnicalAgent': 0.8,
                'TacticAgent': 1.0,
                'RiskAgent': 1.3,         # 情绪波动大，风险上升
                'NewsAgent': 1.2,
                'SectorAgent': 1.0
            },
            'market_regime': {
                'TechnicalAgent': 1.0,
                'TacticAgent': 0.9,
                'RiskAgent': 1.5,         # 市场转换期风险最大
                'NewsAgent': 0.8,
                'SectorAgent': 1.0
            }
        }
        
        # 板块权重矩阵
        self.sector_weights = {
            'AI': {'tech': 1.3, 'news': 1.2, 'policy': 1.5},
            '半导体': {'tech': 1.4, 'news': 1.1, 'policy': 1.8},
            '新能源汽车': {'tech': 1.2, 'news': 1.0, 'policy': 1.4},
            '军工': {'policy': 1.6, 'news': 1.3, 'tech': 0.8},
            '白酒': {'sentiment': 1.2, 'risk': 1.3, 'tech': 0.9},
            '银行': {'risk': 1.5, 'policy': 1.4, 'tech': 0.7},
            '创新药': {'tech': 1.1, 'news': 1.2, 'policy': 1.2},
            '光伏': {'policy': 1.3, 'news': 1.0, 'tech': 1.1}
        }
    
    def get_adjusted_weights(self, base_weights: Dict, event_type: str, 
                            sector: str = None) -> Dict:
        """根据事件类型和板块调整权重"""
        adjusted = base_weights.copy()
        
        # 获取事件影响系数
        event_impacts = self.base_matrix.get(event_type, {})
        
        # 应用事件影响
        for agent, impact in event_impacts.items():
            if agent in adjusted:
                adjusted[agent] *= impact
        
        # 应用板块影响
        if sector and sector in self.sector_weights:
            sector_impacts = self.sector_weights[sector]
            for factor, agents in sector_impacts.items():
                if factor in ['tech', 'news', 'policy']:
                    for agent_name in adjusted:
                        if 'Technical' in agent_name and factor == 'tech':
                            adjusted[agent_name] *= agents
                        elif 'News' in agent_name and factor == 'news':
                            adjusted[agent_name] *= agents
                        elif 'Risk' in agent_name and factor == 'risk':
                            adjusted[agent_name] *= agents
        
        # 归一化
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v/total for k, v in adjusted.items()}
        
        return adjusted

# ==================== 多轮优化器 ====================

class MultiRoundOptimizer:
    """
    多轮迭代权重优化器
    
    流程:
    1. 初始化: 基于先验分布设定初始权重
    2. 第一轮: 使用最大似然估计(MLE)
    3. 第二轮: 贝叶斯更新，融入先验
    4. 第三轮+: 梯度下降优化
    5. 收敛检测: 权重变化 < 阈值
    """
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.agent_names = ["TechnicalAgent", "TacticAgent", "RiskAgent", "NewsAgent"]
        self.performance = {name: AgentPerformance(name) for name in self.agent_names}
        self.event_matrix = EventImpactMatrix()
        self.current_weights = None
        self.optimization_history = []
        self.market_state = "NEUTRAL"
        
    def add_experience(self, agent_name: str, signal: int, actual_return: float):
        """添加经验记录"""
        if agent_name in self.performance:
            self.performance[agent_name].add_record(
                signal, actual_return, datetime.now().isoformat()
            )
    
    def set_market_state(self, state: str):
        """设置市场状态"""
        self.market_state = state
    
    def get_event_adjusted_weights(self, event_type: str = None, sector: str = None) -> Dict:
        """获取事件调整后的权重"""
        if self.current_weights is None:
            self.current_weights = self._initialize_weights()
        
        if event_type:
            weights = self.event_matrix.get_adjusted_weights(
                self.current_weights, event_type, sector
            )
        else:
            weights = self.current_weights.copy()
        
        # 市场状态二次调整
        weights = self._adjust_for_market_regime(weights)
        
        return self._normalize_weights(weights)
    
    def optimize(self) -> Dict[str, float]:
        """
        执行多轮优化
        """
        print(f"\n{'='*70}")
        print(f"🔄 多轮权重优化 | 市场状态: {self.market_state}")
        print(f"{'='*70}")
        
        n_rounds = self.config.max_iterations
        best_weights = None
        best_sharpe = -np.inf
        convergence_count = 0
        
        # 初始化
        weights = self._initialize_weights()
        prior_weights = weights.copy()
        
        for iteration in range(n_rounds):
            # ========== 第一轮: MLE估计 ==========
            mle_weights = self._maximum_likelihood_estimation()
            
            # ========== 第二轮: 贝叶斯更新 ==========
            bayesian_weights = self._bayesian_update(mle_weights, prior_weights)
            
            # ========== 第三轮: 正则化 ==========
            regularized_weights = self._regularize(bayesian_weights)
            
            # ========== 第四轮: 梯度下降 ==========
            gradient_weights = self._gradient_descent(regularized_weights)
            
            # ========== 第五轮: 市场状态调整 ==========
            market_adjusted = self._adjust_for_market_regime(gradient_weights)
            
            # 归一化
            weights = self._normalize_weights(market_adjusted)
            
            # 评估当前权重
            current_sharpe = self._evaluate_weights(weights)
            
            # 保存最优
            if current_sharpe > best_sharpe:
                best_sharpe = current_sharpe
                best_weights = weights.copy()
                convergence_count = 0
            else:
                convergence_count += 1
            
            # 记录历史
            self.optimization_history.append({
                'iteration': iteration,
                'weights': weights.copy(),
                'sharpe': current_sharpe,
                'best_sharpe': best_sharpe
            })
            
            # 打印进度
            if iteration % 20 == 0 or iteration < 5:
                print(f"\n第{iteration}轮:")
                for name, w in weights.items():
                    print(f"  {name}: {w:.4f}")
                print(f"  夏普比率: {current_sharpe:.4f}")
            
            # 收敛检测
            if convergence_count >= 10:
                print(f"\n✅ 第{iteration}轮收敛 (连续{convergence_count}轮无改善)")
                break
            
            # 更新先验
            prior_weights = weights.copy()
        
        self.current_weights = best_weights
        
        print(f"\n{'='*70}")
        print(f"📊 最优权重 (共{len(self.optimization_history)}轮迭代)")
        print(f"{'='*70}")
        for name, w in sorted(best_weights.items(), key=lambda x: -x[1]):
            print(f"  {name}: {w:.4f} ({w*100:.1f}%)")
        print(f"  最优夏普比率: {best_sharpe:.4f}")
        
        return best_weights
    
    def _initialize_weights(self) -> Dict[str, float]:
        """初始化权重 - 使用均匀先验"""
        n = len(self.agent_names)
        return {name: 1.0/n for name in self.agent_names}
    
    def _maximum_likelihood_estimation(self) -> Dict[str, float]:
        """最大似然估计"""
        weights = {}
        total_ic = 0
        ic_values = {}
        
        for name, perf in self.performance.items():
            stats = perf.get_weighted_stats(self.config.time_decay_factor)
            ic = stats['information_coefficient']
            ic_values[name] = max(ic, 0.01)  # 确保正值
            total_ic += ic_values[name]
        
        # IC加权
        for name, ic in ic_values.items():
            weights[name] = ic / total_ic
        
        return weights
    
    def _bayesian_update(self, mle_weights: Dict, prior_weights: Dict) -> Dict[str, float]:
        """贝叶斯更新 - 融合先验"""
        updated = {}
        
        for name in self.agent_names:
            mle = mle_weights.get(name, 0.25)
            prior = prior_weights.get(name, 0.25)
            
            # 贝叶斯更新: posterior ∝ likelihood × prior
            # 使用共轭先验 (Beta分布)
            posterior = 0.7 * mle + 0.3 * prior
            updated[name] = posterior
        
        return self._normalize_weights(updated)
    
    def _regularize(self, weights: Dict) -> Dict[str, float]:
        """正则化防止过拟合"""
        regularized = {}
        
        for name, w in weights.items():
            # L2正则化: 向均值收缩
            mean_w = 1.0 / len(weights)
            reg_w = w * (1 - self.config.regularization) + mean_w * self.config.regularization
            regularized[name] = reg_w
        
        return regularized
    
    def _gradient_descent(self, weights: Dict) -> Dict[str, float]:
        """梯度下降优化"""
        # 计算当前权重的梯度
        gradients = {}
        
        for name, perf in self.performance.items():
            stats = perf.get_weighted_stats(self.config.time_decay_factor)
            
            # 梯度方向: 沿着夏普比率上升的方向
            sharpe = stats['sharpe_ratio']
            
            # 如果夏普比率为正，增加权重；否则减少
            grad = self.config.learning_rate * sharpe
            gradients[name] = weights.get(name, 0.25) + grad
        
        return gradients
    
    def _adjust_for_market_regime(self, weights: Dict) -> Dict[str, float]:
        """根据市场状态调整"""
        adjusted = weights.copy()
        
        if self.market_state == "BEAR":
            # 熊市: 提升RiskAgent权重
            adjusted['RiskAgent'] *= 1.5
            adjusted['TechnicalAgent'] *= 0.8
            adjusted['NewsAgent'] *= 1.2
            
        elif self.market_state == "BULL":
            # 牛市: 提升TechnicalAgent和TacticAgent
            adjusted['TechnicalAgent'] *= 1.3
            adjusted['TacticAgent'] *= 1.2
            adjusted['RiskAgent'] *= 0.8
        
        # NEUTRAL: 不调整
        
        return adjusted
    
    def _normalize_weights(self, weights: Dict) -> Dict[str, float]:
        """归一化权重"""
        total = sum(weights.values())
        if total > 0:
            return {k: v/total for k, v in weights.items()}
        return {name: 1.0/len(weights) for name in weights}
    
    def _evaluate_weights(self, weights: Dict) -> float:
        """评估权重组合的夏普比率"""
        total_sharpe = 0
        total_weight = 0
        
        for name, w in weights.items():
            if name in self.performance:
                stats = self.performance[name].get_weighted_stats()
                total_sharpe += w * stats['sharpe_ratio']
                total_weight += w
        
        return total_sharpe / total_weight if total_weight > 0 else 0
    
    def get_confidence_intervals(self) -> Dict[str, Tuple[float, float]]:
        """计算权重的置信区间"""
        intervals = {}
        
        for name, perf in self.performance.items():
            n = len(perf.signals)
            if n < 10:
                intervals[name] = (0.0, 1.0)
                continue
            
            returns = perf.actual_returns
            
            # Bootstrap置信区间
            np.random.seed(42)
            n_bootstrap = 1000
            bootstrap_means = []
            
            for _ in range(n_bootstrap):
                sample = np.random.choice(returns, size=n, replace=True)
                bootstrap_means.append(np.mean(sample))
            
            lower = np.percentile(bootstrap_means, 
                                  (1 - self.config.confidence_level) / 2 * 100)
            upper = np.percentile(bootstrap_means, 
                                 (1 + self.config.confidence_level) / 2 * 100)
            
            intervals[name] = (lower, upper)
        
        return intervals

# ==================== 主程序 ====================

def simulate_learning():
    """模拟学习过程"""
    print("="*70)
    print("🦐 虾米量化系统 - 自适应多轮权重优化")
    print("="*70)
    
    optimizer = MultiRoundOptimizer()
    
    # 模拟市场状态
    optimizer.set_market_state("NEUTRAL")
    
    # 模拟历史数据 (100笔交易)
    print("\n📊 模拟100笔历史交易...")
    np.random.seed(42)
    
    for i in range(100):
        # 随机生成交易结果
        for agent in optimizer.agent_names:
            # Agent有各自的胜率
            base_win_rates = {
                'TechnicalAgent': 0.55,
                'TacticAgent': 0.50,
                'RiskAgent': 0.60,
                'NewsAgent': 0.52
            }
            
            win_rate = base_win_rates[agent]
            
            # 信号 (BUY: win_rate, HOLD: 0.3, AVOID: 0.7-win_rate)
            signal = np.random.choice([1, 0, -1], p=[win_rate, 0.3, 0.7-win_rate])
            
            # 收益 (考虑信号方向)
            if signal == 1:
                ret = np.random.normal(0.5, 2.0)  # 买入正收益
            elif signal == -1:
                ret = np.random.normal(-0.3, 2.0)  # 卖出/避免负收益
            else:
                ret = np.random.normal(0, 0.5)  # 观望小波动
            
            optimizer.add_experience(agent, signal, ret)
    
    # 测试事件影响
    print("\n" + "="*70)
    print("🧪 事件影响测试")
    print("="*70)
    
    base_weights = optimizer.optimize()
    
    print("\n\n📰 事件调整后的权重:")
    events = ['policy', 'news', 'technical', 'sentiment', 'market_regime']
    
    for event in events:
        adjusted = optimizer.get_event_adjusted_weights(event)
        print(f"\n{event.upper()}事件:")
        for name, w in sorted(adjusted.items(), key=lambda x: -x[1]):
            diff = w - base_weights.get(name, 0)
            sign = "+" if diff >= 0 else ""
            print(f"  {name}: {w:.2%} ({sign}{diff:.2%})")
    
    # 熊市测试
    print("\n\n🐻 熊市权重调整:")
    optimizer.set_market_state("BEAR")
    bear_weights = optimizer.get_event_adjusted_weights('market_regime')
    for name, w in sorted(bear_weights.items(), key=lambda x: -x[1]):
        diff = w - base_weights.get(name, 0)
        sign = "+" if diff >= 0 else ""
        print(f"  {name}: {w:.2%} ({sign}{diff:.2%})")
    
    # 牛市测试
    print("\n\n🐮 牛市权重调整:")
    optimizer.set_market_state("BULL")
    bull_weights = optimizer.get_event_adjusted_weights('market_regime')
    for name, w in sorted(bull_weights.items(), key=lambda x: -x[1]):
        diff = w - base_weights.get(name, 0)
        sign = "+" if diff >= 0 else ""
        print(f"  {name}: {w:.2%} ({sign}{diff:.2%})")
    
    # 置信区间
    print("\n\n📈 权重置信区间 (95%):")
    intervals = optimizer.get_confidence_intervals()
    for name, (lower, upper) in intervals.items():
        base = base_weights.get(name, 0)
        print(f"  {name}: [{lower:.2%}, {upper:.2%}] (当前: {base:.2%})")

if __name__ == "__main__":
    simulate_learning()
