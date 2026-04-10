#!/usr/bin/env python3
"""
虾米量化系统 - 动态权重优化器
Dynamic Weight Optimizer

基于历史信号数据，使用均值-方差优化(MVO)计算最优权重
每100笔交易重新校准一次

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
import os

@dataclass
class AgentStats:
    """Agent统计数据"""
    name: str
    signal_history: List[int]  # 1=BUY, 0=HOLD, -1=AVOID
    pnl_history: List[float]    # 每笔交易的盈亏
    
    # 计算属性
    @property
    def win_rate(self) -> float:
        """胜率"""
        if not self.pnl_history:
            return 0.5
        return sum(1 for p in self.pnl_history if p > 0) / len(self.pnl_history)
    
    @property
    def mean_return(self) -> float:
        """平均收益"""
        if not self.pnl_history:
            return 0.0
        return np.mean(self.pnl_history)
    
    @property
    def std_return(self) -> float:
        """收益标准差(风险)"""
        if len(self.pnl_history) < 2:
            return 1.0
        return np.std(self.pnl_history, ddof=1)
    
    @property
    def sharpe_ratio(self) -> float:
        """夏普比率 (收益/风险)"""
        if self.std_return == 0:
            return 0
        return self.mean_return / self.std_return
    
    @property
    def signal_accuracy(self) -> float:
        """信号准确率 (BUY信号的最终涨跌)"""
        if not self.signal_history:
            return 0.5
        correct = sum(1 for s in self.signal_history if s != 0)
        return correct / len(self.signal_history) if self.signal_history else 0.5


class DynamicWeightOptimizer:
    """
    动态权重优化器
    
    基于历史信号数据，使用多种统计方法计算最优权重：
    1. 均值-方差优化 (Mean-Variance Optimization)
    2. 风险平价 (Risk Parity)
    3. 信息比率加权 (Information Ratio Weighting)
    """
    
    def __init__(self, history_file: str = "agent_signal_history.json"):
        self.history_file = history_file
        self.agent_names = ["TechnicalAgent", "TacticAgent", "RiskAgent", "NewsAgent"]
        self.agent_stats = {name: AgentStats(name, [], []) for name in self.agent_names}
        self.weights = None
        self.last_optimization = None
        self.trade_count = 0
        self.rebalance_threshold = 100  # 每100笔交易重新优化
        
        self._load_history()
    
    def _load_history(self):
        """加载历史数据"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    
                # 重建统计数据
                for agent_name in self.agent_names:
                    if agent_name in data:
                        agent_data = data[agent_name]
                        self.agent_stats[agent_name] = AgentStats(
                            name=agent_name,
                            signal_history=agent_data.get('signals', []),
                            pnl_history=agent_data.get('pnl', [])
                        )
                
                self.trade_count = data.get('trade_count', 0)
                self.last_optimization = data.get('last_optimization')
                
                print(f"✅ 加载历史数据: {self.trade_count} 笔交易")
            except Exception as e:
                print(f"加载历史失败: {e}")
    
    def _save_history(self):
        """保存历史数据"""
        data = {
            'trade_count': self.trade_count,
            'last_optimization': self.last_optimization,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        for name, stats in self.agent_stats.items():
            data[name] = {
                'signals': stats.signal_history,
                'pnl': stats.pnl_history
            }
        
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_signal(self, agent_name: str, signal: int, pnl: float = 0):
        """
        记录Agent信号和盈亏
        signal: 1=BUY, 0=HOLD, -1=AVOID
        pnl: 该信号对应的盈亏(后续填入)
        """
        if agent_name in self.agent_stats:
            self.agent_stats[agent_name].signal_history.append(signal)
            if pnl != 0:
                self.agent_stats[agent_name].pnl_history.append(pnl)
    
    def record_trade_result(self, agent_signals: Dict[str, int], actual_pnl: float):
        """
        记录交易结果，更新所有Agent数据
        agent_signals: {agent_name: signal}
        actual_pnl: 实际盈亏
        """
        self.trade_count += 1
        
        # 归一化盈亏到各Agent
        for name, signal in agent_signals.items():
            if name in self.agent_stats:
                # 只有BUY信号才记录盈亏
                if signal == 1:
                    self.agent_stats[name].pnl_history.append(actual_pnl)
                else:
                    # 非BUY信号记录0
                    self.agent_stats[name].pnl_history.append(0)
        
        self._save_history()
        
        # 检查是否需要重新优化
        if self.trade_count % self.rebalance_threshold == 0:
            self.optimize()
    
    def optimize(self) -> Dict[str, float]:
        """
        优化权重 - 基于均值-方差优化
        返回: {agent_name: weight}
        """
        print(f"\n{'='*60}")
        print(f"📊 动态权重优化 | 交易笔数: {self.trade_count}")
        print(f"{'='*60}")
        
        # 打印各Agent统计
        print("\n各Agent历史表现:")
        print("-" * 60)
        for name, stats in self.agent_stats.items():
            print(f"{name}:")
            print(f"  信号数: {len(stats.signal_history)}")
            print(f"  胜率: {stats.win_rate:.1%}")
            print(f"  平均收益: {stats.mean_return:+.2f}%")
            print(f"  标准差: {stats.std_return:.2f}%")
            print(f"  夏普比率: {stats.sharpe_ratio:.3f}")
        
        # 构建收益矩阵
        returns_matrix = []
        valid_agents = []
        
        for name, stats in self.agent_stats.items():
            if len(stats.pnl_history) >= 10:  # 至少10笔数据
                returns_matrix.append(stats.pnl_history)
                valid_agents.append(name)
        
        if len(returns_matrix) < 2:
            print("\n⚠️ 数据不足，使用默认权重")
            return self._default_weights()
        
        returns_matrix = np.array(returns_matrix).T  # 列=Agent
        
        # 计算均值和协方差
        mean_returns = np.mean(returns_matrix, axis=0)
        cov_matrix = np.cov(returns_matrix.T)
        
        # 方法1: 均值-方差优化 (最大化夏普比率)
        weights_mvo = self._mean_variance_optimization(mean_returns, cov_matrix)
        
        # 方法2: 风险平价
        weights_rp = self._risk_parity(cov_matrix)
        
        # 方法3: 信息比率加权
        weights_ir = self._information_ratio_weighting(mean_returns, cov_matrix)
        
        # 综合三种方法 (等权重)
        final_weights = (weights_mvo + weights_rp + weights_ir) / 3
        
        # 确保权重为正且和为1
        final_weights = np.maximum(final_weights, 0.01)
        final_weights = final_weights / final_weights.sum()
        
        # 映射回原Agent名
        result = {}
        for i, name in enumerate(valid_agents):
            result[name] = round(float(final_weights[i]), 4)
        
        # 填充未参与的Agent
        for name in self.agent_names:
            if name not in result:
                result[name] = 0.0
        
        self.weights = result
        self.last_optimization = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n优化完成时间: {self.last_optimization}")
        print(f"\n最优权重:")
        print("-" * 40)
        for name, w in sorted(result.items(), key=lambda x: -x[1]):
            print(f"  {name}: {w:.2%}")
        
        # 保存优化结果
        self._save_history()
        
        return result
    
    def _mean_variance_optimization(self, mean_returns: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
        """
        均值-方差优化 (Mean-Variance Optimization)
        目标: 最大化夏普比率
        """
        n = len(mean_returns)
        
        # 排除无效协方差矩阵
        if np.any(np.isnan(cov_matrix)) or np.any(np.isinf(cov_matrix)):
            return np.ones(n) / n
        
        try:
            # 使用简化的优化方法
            # 目标函数: 最大化 (mu^T * w) / sqrt(w^T * Sigma * w)
            # 即最大化 (mu^T * w)^2 / (w^T * Sigma * w)
            
            inv_cov = np.linalg.pinv(cov_matrix)  # 伪逆
            
            # 最优权重: proportional to (inv_cov * mu)
            weights = inv_cov @ mean_returns
            
            # 确保为正
            weights = np.maximum(weights, 0.01)
            
            # 归一化
            weights = weights / weights.sum()
            
            return weights
            
        except Exception as e:
            print(f"MVO失败: {e}")
            return np.ones(n) / n
    
    def _risk_parity(self, cov_matrix: np.ndarray) -> np.ndarray:
        """
        风险平价 (Risk Parity)
        每个Agent对组合风险的贡献相等
        """
        n = len(cov_matrix)
        
        try:
            # 简化版: 权重与波动率成反比
            variances = np.diag(cov_matrix)
            stds = np.sqrt(np.maximum(variances, 0.001))
            
            weights = 1.0 / stds
            weights = weights / weights.sum()
            
            return weights
            
        except Exception as e:
            print(f"风险平价失败: {e}")
            return np.ones(n) / n
    
    def _information_ratio_weighting(self, mean_returns: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
        """
        信息比率加权
        权重与信息比率(IR = mu/std)成正比
        """
        n = len(mean_returns)
        
        try:
            stds = np.sqrt(np.maximum(np.diag(cov_matrix), 0.001))
            ir = mean_returns / stds
            
            # 只用正值IR
            weights = np.maximum(ir, 0.01)
            weights = weights / weights.sum()
            
            return weights
            
        except Exception as e:
            print(f"IR加权失败: {e}")
            return np.ones(n) / n
    
    def _default_weights(self) -> Dict[str, float]:
        """默认权重"""
        return {
            "TechnicalAgent": 0.30,
            "TacticAgent": 0.30,
            "RiskAgent": 0.25,
            "NewsAgent": 0.15
        }
    
    def get_weights(self) -> Dict[str, float]:
        """获取当前权重"""
        if self.weights is None or self.trade_count % self.rebalance_threshold == 0:
            # 需要重新优化
            if self.trade_count >= 10:
                self.optimize()
            else:
                self.weights = self._default_weights()
        
        return self.weights
    
    def get_agent_weight(self, agent_name: str) -> float:
        """获取单个Agent权重"""
        weights = self.get_weights()
        return weights.get(agent_name, 0.25)


def test_optimizer():
    """测试优化器"""
    print("="*60)
    print("动态权重优化器测试")
    print("="*60)
    
    optimizer = DynamicWeightOptimizer()
    
    # 模拟一些历史数据
    print("\n📝 模拟历史数据...")
    
    # 模拟30笔交易
    np.random.seed(42)
    
    for i in range(30):
        # 随机生成信号
        signals = {
            "TechnicalAgent": np.random.choice([1, 0, -1], p=[0.4, 0.4, 0.2]),
            "TacticAgent": np.random.choice([1, 0, -1], p=[0.35, 0.45, 0.2]),
            "RiskAgent": np.random.choice([1, 0, -1], p=[0.3, 0.5, 0.2]),
            "NewsAgent": np.random.choice([1, 0, -1], p=[0.25, 0.5, 0.25])
        }
        
        # 随机盈亏
        pnl = np.random.normal(0.5, 2.0)
        
        optimizer.record_trade_result(signals, pnl)
    
    # 优化
    weights = optimizer.optimize()
    
    print("\n📊 最终权重:")
    for name, w in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {name}: {w:.2%}")


if __name__ == "__main__":
    test_optimizer()
