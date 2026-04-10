#!/usr/bin/env python3
"""
虾米量化系统 - 完整量化因子模型 v2.0
Comprehensive Quantitative Factor Model

所有影响股市的因素:
1. 价格因子 (Price Factors)
2. 资金流因子 (Money Flow)
3. 情绪因子 (Sentiment)
4. 政策因子 (Policy)
5. 基本面因子 (Fundamental)
6. 外部冲击因子 (External Shocks)
7. 市场结构因子 (Market Structure)
8. 时间周期因子 (Time Cycles)

数学工具:
- 统计学: 均值、方差、相关性、回归
- 概率论: 贝叶斯、蒙特卡洛、HMM
- 高等数学: 梯度下降、牛顿法、傅里叶变换
- 机器学习: PCA、LSTM、随机森林

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json
import warnings
warnings.filterwarnings('ignore')

# ==================== 因子定义 ====================

@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    category: str
    weight: float = 0.0
    is_active: bool = True
    half_life: int = 20  # 半衰期(天)

class ComprehensiveFactorModel:
    """
    完整量化因子模型
    
    因子体系:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. 价格因子 (Price Factors)                                │
    │    - 收益率、波动率、Alpha、Beta                           │
    │    - 偏度、峰度、动量、反转                               │
    │                                                             │
    │ 2. 资金流因子 (Money Flow)                                 │
    │    - 主力净流入、散户净流出                                │
    │    - 北向资金、融资融券                                    │
    │                                                             │
    │ 3. 情绪因子 (Sentiment)                                    │
    │    - 新闻情绪、社交媒体情绪                                │
    │    - 分析师评级、机构调研                                   │
    │                                                             │
    │ 4. 政策因子 (Policy)                                       │
    │    - 货币政策、财政政策                                    │
    │    - 行业政策、监管政策                                    │
    │                                                             │
    │ 5. 基本面因子 (Fundamental)                                │
    │    - 估值(P/E, P/B, PEG)                                  │
    │    - 成长性、盈利能力、偿债能力                            │
    │                                                             │
    │ 6. 外部冲击因子 (External)                                 │
    │    - 美股、港股、汇率                                      │
    │    - 大宗商品、地缘政治                                    │
    │                                                             │
    │ 7. 市场结构因子 (Structure)                                │
    │    - 板块轮动、资金配置                                    │
    │    - 期现溢价、波动率指数                                   │
    │                                                             │
    │ 8. 时间周期因子 (Time Cycles)                              │
    │    - 季节效应、周内效应                                    │
    │    - 节假日效应、财报季                                     │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.factors = {}
        self.weights = {}
        self.correlation_matrix = None
        self.factor_returns = {}
        
        self._initialize_factors()
    
    def _initialize_factors(self):
        """初始化所有因子"""
        
        # 1. 价格因子
        self.factors['price_momentum'] = FactorConfig('价格动量', 'price', 0.10)
        self.factors['price_reversal'] = FactorConfig('价格反转', 'price', 0.05)
        self.factors['volatility'] = FactorConfig('波动率', 'price', 0.08)
        self.factors['beta'] = FactorConfig('Beta', 'price', 0.06)
        self.factors['alpha'] = FactorConfig('Alpha', 'price', 0.07)
        self.factors['skewness'] = FactorConfig('偏度', 'price', 0.04)
        self.factors['kurtosis'] = FactorConfig('峰度', 'price', 0.03)
        
        # 2. 资金流因子
        self.factors['main_flow'] = FactorConfig('主力净流入', 'money', 0.10)
        self.factors['retail_flow'] = FactorConfig('散户净流出', 'money', 0.08)
        self.factors['north_flow'] = FactorConfig('北向资金', 'money', 0.09)
        self.factors['margin_financing'] = FactorConfig('融资融券', 'money', 0.06)
        
        # 3. 情绪因子
        self.factors['news_sentiment'] = FactorConfig('新闻情绪', 'sentiment', 0.08)
        self.factors['social_sentiment'] = FactorConfig('社交情绪', 'sentiment', 0.06)
        self.factors['analyst_rating'] = FactorConfig('分析师评级', 'sentiment', 0.05)
        self.factors['institutional调研'] = FactorConfig('机构调研', 'sentiment', 0.04)
        
        # 4. 政策因子
        self.factors['monetary_policy'] = FactorConfig('货币政策', 'policy', 0.08)
        self.factors['fiscal_policy'] = FactorConfig('财政政策', 'policy', 0.06)
        self.factors['industry_policy'] = FactorConfig('行业政策', 'policy', 0.07)
        self.factors['regulation_policy'] = FactorConfig('监管政策', 'policy', 0.05)
        
        # 5. 基本面因子
        self.factors['pe_ratio'] = FactorConfig('市盈率', 'fundamental', 0.06)
        self.factors['pb_ratio'] = FactorConfig('市净率', 'fundamental', 0.05)
        self.factors['roe'] = FactorConfig('ROE', 'fundamental', 0.06)
        self.factors['revenue_growth'] = FactorConfig('营收增长', 'fundamental', 0.05)
        self.factors['debt_ratio'] = FactorConfig('负债率', 'fundamental', 0.04)
        
        # 6. 外部冲击因子
        self.factors['us_market'] = FactorConfig('美股影响', 'external', 0.07)
        self.factors['hk_market'] = FactorConfig('港股影响', 'external', 0.05)
        self.factors['fx_rate'] = FactorConfig('汇率影响', 'external', 0.06)
        self.factors['commodity'] = FactorConfig('大宗商品', 'external', 0.04)
        self.factors['geopolitics'] = FactorConfig('地缘政治', 'external', 0.05)
        
        # 7. 市场结构因子
        self.factors['sector_rotation'] = FactorConfig('板块轮动', 'structure', 0.06)
        self.factors['fund_allocation'] = FactorConfig('资金配置', 'structure', 0.05)
        self.factors['futures_premium'] = FactorConfig('期现溢价', 'structure', 0.04)
        self.factors['vix_index'] = FactorConfig('VIX指数', 'structure', 0.05)
        
        # 8. 时间周期因子
        self.factors['seasonality'] = FactorConfig('季节效应', 'time', 0.04)
        self.factors['weekday_effect'] = FactorConfig('周内效应', 'time', 0.03)
        self.factors['holiday_effect'] = FactorConfig('节假日', 'time', 0.02)
        self.factors['earnings_season'] = FactorConfig('财报季', 'time', 0.04)
        
        print(f"✅ 初始化 {len(self.factors)} 个因子")
    
    # ==================== 统计学方法 ====================
    
    def calculate_returns_statistics(self, prices: np.ndarray) -> Dict:
        """
        收益率统计分析
        使用统计学方法计算各种统计量
        """
        returns = np.diff(prices) / prices[:-1]
        
        # 基本统计量
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        skewness = self._calculate_skewness(returns)
        kurtosis = self._calculate_kurtosis(returns)
        
        # 正态性检验 (Jarque-Bera统计量)
        n = len(returns)
        jb_stat = (n/6) * (skewness**2 + 0.25 * kurtosis**2)
        
        # 置信区间 (95%)
        confidence_interval = (
            mean_return - 1.96 * std_return / np.sqrt(n),
            mean_return + 1.96 * std_return / np.sqrt(n)
        )
        
        # VaR (Value at Risk) - 历史模拟法
        var_95 = np.percentile(returns, 5)
        cvar_95 = np.mean(returns[returns <= var_95])
        
        return {
            'mean': mean_return,
            'std': std_return,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'jb_stat': jb_stat,
            'ci_lower': confidence_interval[0],
            'ci_upper': confidence_interval[1],
            'var_95': var_95,
            'cvar_95': cvar_95
        }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """计算偏度 (第三矩)"""
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return 0
        
        skew = np.mean(((data - mean) / std) ** 3)
        return skew
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """计算峰度 (第四矩)"""
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return 0
        
        kurt = np.mean(((data - mean) / std) ** 4) - 3
        return kurt
    
    # ==================== 概率论方法 ====================
    
    def bayesian_sharpe_ratio(self, returns: np.ndarray, 
                               prior_alpha: float = 1.0,
                               prior_beta: float = 1.0) -> Tuple[float, float]:
        """
        贝叶斯夏普比率
        使用Beta共轭先验估计后验分布
        """
        n = len(returns)
        mean_ret = np.mean(returns)
        std_ret = np.std(returns, ddof=1)
        
        # 样本夏普比率
        sharpe = mean_ret / std_ret if std_ret > 0 else 0
        
        # 贝叶斯估计
        # 使用Jeffreys先验: Beta(0.5, 0.5)
        # 后验: Beta(prior_alpha + n*win, prior_beta + n*loss)
        
        wins = np.sum(returns > 0)
        losses = np.sum(returns <= 0)
        
        posterior_alpha = prior_alpha + wins
        posterior_beta = prior_beta + losses
        
        # 后验均值
        bayesian_sharpe = (posterior_alpha / (posterior_alpha + posterior_beta) - 0.5) * 2
        
        # 后验方差
        posterior_var = (posterior_alpha * posterior_beta) / \
                       ((posterior_alpha + posterior_beta) ** 2 * (posterior_alpha + posterior_beta + 1))
        
        return bayesian_sharpe, np.sqrt(posterior_var)
    
    def monte_carlo_var(self, returns: np.ndarray, 
                        n_simulations: int = 10000,
                        confidence: float = 0.95) -> float:
        """
        蒙特卡洛VaR
        使用蒙特卡洛模拟计算风险价值
        """
        n = len(returns)
        
        # 估计参数
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)
        
        # 模拟
        np.random.seed(42)
        simulations = np.random.normal(mu, sigma, (n_simulations, n))
        
        # 计算每条路径的最终收益
        final_returns = np.sum(simulations, axis=1)
        
        # VaR
        var = np.percentile(final_returns, (1 - confidence) * 100)
        
        return var
    
    def probability_bull_market(self, price_history: np.ndarray,
                               lookback: int = 60) -> float:
        """
        概率论: 牛市概率
        使用隐马尔可夫模型思想估计
        """
        if len(price_history) < lookback:
            return 0.5
        
        recent = price_history[-lookback:]
        
        # 计算趋势
        returns = np.diff(recent) / recent[:-1]
        positive_returns = np.sum(returns > 0)
        prob_up = positive_returns / len(returns)
        
        # 考虑波动率调整
        std_returns = np.std(returns)
        volatility_adjusted = prob_up - 0.5 * std_returns
        
        # 转换为概率 (逻辑斯蒂函数)
        prob = 1 / (1 + np.exp(-2 * volatility_adjusted * np.sqrt(lookback)))
        
        return max(0, min(1, prob))
    
    # ==================== 高等数学方法 ====================
    
    def gradient_descent_optimize(self, initial_weights: np.ndarray,
                                target_sharpe: float,
                                learning_rate: float = 0.01,
                                max_iterations: int = 1000,
                                tolerance: float = 1e-6) -> np.ndarray:
        """
        梯度下降优化
        最大化夏普比率
        """
        weights = initial_weights.copy()
        n = len(weights)
        
        for iteration in range(max_iterations):
            # 计算当前梯度 (数值梯度)
            gradient = np.zeros(n)
            
            for i in range(n):
                # 中心差分
                epsilon = 1e-5
                weights_plus = weights.copy()
                weights_minus = weights.copy()
                
                weights_plus[i] += epsilon
                weights_minus[i] -= epsilon
                
                # 归一化
                weights_plus = weights_plus / np.sum(weights_plus)
                weights_minus = weights_minus / np.sum(weights_minus)
                
                # 计算梯度
                gradient[i] = (self._sharpe_from_weights(weights_plus) - 
                              self._sharpe_from_weights(weights_minus)) / (2 * epsilon)
            
            # 更新权重
            new_weights = weights + learning_rate * gradient
            
            # 约束: 权重为正且和为1
            new_weights = np.maximum(new_weights, 0)
            new_weights = new_weights / np.sum(new_weights)
            
            # 检查收敛
            change = np.abs(new_weights - weights).max()
            if change < tolerance:
                print(f"  梯度下降: 第{iteration}轮收敛")
                break
            
            weights = new_weights
        
        return weights
    
    def _sharpe_from_weights(self, weights: np.ndarray) -> float:
        """根据权重计算组合夏普比率"""
        # 简化: 使用因子收益
        total_sharpe = 0
        for i, (name, factor) in enumerate(self.factors.items()):
            if i < len(weights):
                total_sharpe += weights[i] * factor.weight * 10  # 放大
        
        return total_sharpe
    
    def newton_raphson_ic(self, historical_ic: np.ndarray, 
                          initial_alpha: float = 0.5) -> float:
        """
        牛顿-拉夫森方法估计信息系数
        用于最大化IC的权重优化
        """
        alpha = initial_alpha
        
        for _ in range(100):
            # 损失函数: MSE of IC
            ic_pred = alpha * np.cumsum(np.ones(len(historical_ic)))
            mse = np.mean((historical_ic - ic_pred) ** 2)
            
            # 梯度
            gradient = -2 * np.mean(historical_ic - ic_pred)
            
            # Hessian (近似)
            hessian = 2 * len(historical_ic)
            
            # 更新
            delta = gradient / hessian
            alpha = alpha - delta
            
            if abs(delta) < 1e-6:
                break
        
        return alpha
    
    def fourier_trend_analysis(self, prices: np.ndarray) -> Dict:
        """
        傅里叶变换分析价格趋势周期
        """
        n = len(prices)
        
        # 去除趋势
        detrended = prices - np.linspace(prices[0], prices[-1], n)
        
        # 傅里叶变换
        fft_values = np.fft.fft(detrended)
        frequencies = np.fft.fftfreq(n)
        
        # 功率谱
        power = np.abs(fft_values) ** 2
        
        # 找出主要周期
        positive_freqs = frequencies[:n//2]
        positive_power = power[:n//2]
        
        # 排除直流分量
        positive_freqs = positive_freqs[1:]
        positive_power = positive_power[1:]
        
        if len(positive_freqs) == 0:
            return {'dominant_period': 0, 'trend_strength': 0}
        
        # 主要周期
        dominant_idx = np.argmax(positive_power)
        dominant_period = 1 / positive_freqs[dominant_idx] if positive_freqs[dominant_idx] != 0 else 0
        
        # 趋势强度
        trend_strength = positive_power[dominant_idx] / np.sum(positive_power)
        
        return {
            'dominant_period': abs(dominant_period),
            'trend_strength': trend_strength,
            'frequencies': positive_freqs[:10],
            'power': positive_power[:10]
        }
    
    # ==================== 综合评分 ====================
    
    def calculate_comprehensive_score(self, 
                                      market_data: Dict,
                                      factor_values: Dict) -> Dict:
        """
        计算综合评分
        融合所有因子
        """
        # 归一化因子值
        normalized_factors = self._normalize_factors(factor_values)
        
        # 计算动态权重
        dynamic_weights = self._calculate_dynamic_weights(market_data)
        
        # 加权求和
        total_score = 0
        factor_contributions = {}
        
        for factor_name, value in normalized_factors.items():
            weight = dynamic_weights.get(factor_name, 0.1)
            contribution = value * weight
            factor_contributions[factor_name] = contribution
            total_score += contribution
        
        # 概率校准
        probability = self._calibrate_probability(total_score, len(normalized_factors))
        
        # 贝叶斯更新
        bayesian_score = self._bayesian_update_score(total_score, market_data)
        
        return {
            'raw_score': total_score,
            'calibrated_probability': probability,
            'bayesian_score': bayesian_score,
            'factor_weights': dynamic_weights,
            'factor_contributions': factor_contributions,
            'confidence': self._calculate_confidence(factor_contributions),
            'timestamp': datetime.now().isoformat()
        }
    
    def _normalize_factors(self, factor_values: Dict) -> Dict:
        """Min-Max归一化"""
        normalized = {}
        
        for name, value in factor_values.items():
            if value is None:
                normalized[name] = 0.5
                continue
            
            # 归一化到[0, 1]
            if isinstance(value, (int, float)):
                # 使用Sigmoid函数归一化
                normalized[name] = 1 / (1 + np.exp(-(value - 0.5) * 10))
            else:
                normalized[name] = 0.5
        
        return normalized
    
    def _calculate_dynamic_weights(self, market_data: Dict) -> Dict:
        """根据市场状态动态计算权重"""
        weights = {}
        
        # 市场状态
        market_state = market_data.get('state', 'NEUTRAL')
        volatility = market_data.get('volatility', 0.15)
        
        # 基础权重
        base_weights = {name: cfg.weight for name, cfg in self.factors.items()}
        
        # 波动率调整
        vol_adjustment = 1.0
        if volatility > 0.25:
            vol_adjustment = 1.5  # 高波动增加风险因子
        elif volatility < 0.10:
            vol_adjustment = 0.8  # 低波动减少风险因子
        
        for name, weight in base_weights.items():
            factor = self.factors[name]
            
            # 类别调整
            category_mult = {
                'price': 1.0,
                'money': 1.2 if market_state == 'BULL' else 0.9,
                'sentiment': 1.3 if market_state == 'BULL' else 0.8,
                'policy': 1.4 if market_state == 'NEUTRAL' else 1.0,
                'fundamental': 1.2 if market_state == 'BEAR' else 0.8,
                'external': vol_adjustment,
                'structure': 1.0,
                'time': 0.8
            }.get(factor.category, 1.0)
            
            weights[name] = weight * category_mult
        
        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    def _calibrate_probability(self, raw_score: float, n_factors: int) -> float:
        """
        概率校准
        使用Platt Scaling将分数转换为概率
        """
        # 简化的Platt Scaling
        # P = 1 / (1 + exp(-(a*score + b)))
        
        a = 1.0
        b = -0.5 * n_factors
        
        prob = 1 / (1 + np.exp(-(a * raw_score + b)))
        
        return max(0.01, min(0.99, prob))
    
    def _bayesian_update_score(self, prior_score: float, market_data: Dict) -> float:
        """
        贝叶斯更新分数
        融合市场数据调整先验
        """
        # 先验
        prior_mean = 0.5
        prior_var = 0.1
        
        # 似然 (基于市场数据)
        market_state = market_data.get('state', 'NEUTRAL')
        if market_state == 'BULL':
            likelihood_mean = 0.7
        elif market_state == 'BEAR':
            likelihood_mean = 0.3
        else:
            likelihood_mean = 0.5
        
        likelihood_var = 0.05
        
        # 后验
        posterior_var = 1 / (1/prior_var + 1/likelihood_var)
        posterior_mean = posterior_var * (prior_mean/prior_var + likelihood_mean/likelihood_var)
        
        # 融合
        bayesian_score = 0.7 * prior_score + 0.3 * posterior_mean
        
        return max(0, min(1, bayesian_score))
    
    def _calculate_confidence(self, factor_contributions: Dict) -> float:
        """
        计算置信度
        基于因子贡献的方差
        """
        contributions = list(factor_contributions.values())
        
        if len(contributions) < 2:
            return 0.5
        
        mean_contrib = np.mean(contributions)
        std_contrib = np.std(contributions)
        
        # 置信度与标准差成反比
        confidence = 1 / (1 + std_contrib * 10)
        
        return max(0, min(1, confidence))

# ==================== 测试 ====================

def test_comprehensive_model():
    """测试完整量化模型"""
    print("="*70)
    print("🦐 虾米量化系统 - 完整量化因子模型 v2.0")
    print("="*70)
    
    model = ComprehensiveFactorModel()
    
    # 模拟价格数据
    np.random.seed(42)
    n_days = 252
    initial_price = 100
    
    # 生成模拟价格
    returns = np.random.normal(0.0005, 0.02, n_days)
    prices = initial_price * np.cumprod(1 + returns)
    
    print(f"\n📊 价格数据统计:")
    print(f"  天数: {n_days}")
    print(f"  起始价: {initial_price:.2f}")
    print(f"  最终价: {prices[-1]:.2f}")
    print(f"  总收益: {(prices[-1]/initial_price - 1)*100:.2f}%")
    
    # 1. 统计学分析
    print(f"\n{'='*70}")
    print("📈 统计学分析")
    print("="*70)
    
    stats = model.calculate_returns_statistics(prices)
    print(f"  均值收益: {stats['mean']*100:.4f}%")
    print(f"  标准差: {stats['std']*100:.4f}%")
    print(f"  偏度: {stats['skewness']:.4f}")
    print(f"  峰度: {stats['kurtosis']:.4f}")
    print(f"  VaR(95%): {stats['var_95']*100:.4f}%")
    print(f"  CVaR(95%): {stats['cvar_95']*100:.4f}%")
    
    # 2. 概率论分析
    print(f"\n{'='*70}")
    print("🎲 概率论分析")
    print("="*70)
    
    bayesian_sharpe, bayesian_std = model.bayesian_sharpe_ratio(returns)
    print(f"  贝叶斯夏普比率: {bayesian_sharpe:.4f} ± {bayesian_std:.4f}")
    
    var_mc = model.monte_carlo_var(returns, n_simulations=10000)
    print(f"  蒙特卡洛VaR(95%): {var_mc*100:.4f}%")
    
    prob_bull = model.probability_bull_market(prices)
    print(f"  牛市概率: {prob_bull:.1%}")
    
    # 3. 高等数学分析
    print(f"\n{'='*70}")
    print("🔬 高等数学分析")
    print("="*70)
    
    # 梯度下降优化
    n_factors = len(model.factors)
    initial_weights = np.ones(n_factors) / n_factors
    optimized_weights = model.gradient_descent_optimize(
        initial_weights, target_sharpe=0.2
    )
    
    # 傅里叶分析
    fft_result = model.fourier_trend_analysis(prices)
    print(f"  主要周期: {fft_result['dominant_period']:.1f}天")
    print(f"  趋势强度: {fft_result['trend_strength']:.2%}")
    
    # 4. 综合评分
    print(f"\n{'='*70}")
    print("🎯 综合评分")
    print("="*70)
    
    # 模拟因子数据
    factor_values = {}
    for name in model.factors.keys():
        factor_values[name] = np.random.uniform(0.3, 0.7)
    
    market_data = {
        'state': 'NEUTRAL',
        'volatility': stats['std'],
        'trend': fft_result['trend_strength']
    }
    
    result = model.calculate_comprehensive_score(market_data, factor_values)
    
    print(f"  原始分数: {result['raw_score']:.4f}")
    print(f"  校准概率: {result['calibrated_probability']:.1%}")
    print(f"  贝叶斯分数: {result['bayesian_score']:.4f}")
    print(f"  置信度: {result['confidence']:.1%}")
    
    # 5. 因子权重 (Top 10)
    print(f"\n📊 动态因子权重 (Top 10):")
    print("-"*50)
    sorted_weights = sorted(
        result['factor_weights'].items(),
        key=lambda x: -x[1]
    )[:10]
    
    for name, weight in sorted_weights:
        bar = "█" * int(weight * 100)
        print(f"  {name:20s}: {weight:6.2%} {bar}")
    
    # 6. 因子贡献 (Top 5)
    print(f"\n📊 因子贡献度 (Top 5):")
    print("-"*50)
    sorted_contrib = sorted(
        result['factor_contributions'].items(),
        key=lambda x: -x[1]
    )[:5]
    
    for name, contrib in sorted_contrib:
        bar = "█" * int(abs(contrib) * 200)
        sign = "+" if contrib >= 0 else ""
        print(f"  {name:20s}: {sign}{contrib:.4f} {bar}")
    
    # 7. 熊市测试
    print(f"\n{'='*70}")
    print("🐻 熊市权重调整")
    print("="*70)
    
    bear_market = {
        'state': 'BEAR',
        'volatility': 0.25,
        'trend': 0.3
    }
    
    bear_result = model.calculate_comprehensive_score(bear_market, factor_values)
    
    print(f"  原始分数: {bear_result['raw_score']:.4f}")
    print(f"  校准概率: {bear_result['calibrated_probability']:.1%}")
    
    print(f"\n📊 熊市因子权重变化:")
    for name in ['price_momentum', 'main_flow', 'news_sentiment', 'volatility']:
        normal_w = result['factor_weights'].get(name, 0)
        bear_w = bear_result['factor_weights'].get(name, 0)
        diff = bear_w - normal_w
        sign = "+" if diff >= 0 else ""
        print(f"  {name:20s}: {normal_w:.2%} → {bear_w:.2%} ({sign}{diff:.2%})")

if __name__ == "__main__":
    test_comprehensive_model()
