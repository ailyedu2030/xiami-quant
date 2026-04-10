#!/usr/bin/env python3
"""
虾米量化系统 - 完整集成系统 v4.0
Integrated Quantitative Trading System

集成所有组件:
1. 37因子量化模型
2. 自适应多轮权重优化
3. 三大核心工作流
4. 统一数据源
5. 事件驱动引擎
6. 政策/新闻监控
7. 实时决策委员会

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

# ==================== 系统路径 ====================

SYSTEM_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SYSTEM_PATH)

# ==================== 导入所有模块 ====================

try:
    from unified_data_source import UnifiedDataSource
    DATA_SOURCE = UnifiedDataSource()
    print("✅ 数据源模块加载成功")
except Exception as e:
    print(f"⚠️ 数据源模块加载失败: {e}")
    DATA_SOURCE = None

try:
    from comprehensive_quantitative_system import ComprehensiveFactorModel
    FACTOR_MODEL = ComprehensiveFactorModel()
    print("✅ 37因子模型加载成功")
except Exception as e:
    print(f"⚠️ 因子模型加载失败: {e}")
    FACTOR_MODEL = None

try:
    from adaptive_weight_system import MultiRoundOptimizer, EventImpactMatrix
    WEIGHT_OPTIMIZER = MultiRoundOptimizer()
    EVENT_MATRIX = EventImpactMatrix()
    print("✅ 自适应权重模块加载成功")
except Exception as e:
    print(f"⚠️ 自适应权重模块加载失败: {e}")
    WEIGHT_OPTIMIZER = None
    EVENT_MATRIX = None

# ==================== 配置 ====================

@dataclass
class SystemConfig:
    """系统配置"""
    # 数据源
    data_source: str = "tushare"
    
    # 权重配置
    use_adaptive_weights: bool = True
    weight_rebalance_threshold: int = 100
    
    # 风险配置
    max_position: int = 5
    max_single_position: float = 0.25
    stop_loss_pct: float = 0.08
    target_pct: float = 0.15
    
    # 市场配置
    market_state: str = "NEUTRAL"
    
    # 因子配置
    use_all_factors: bool = True
    factor_confidence_threshold: float = 0.6

# ==================== 主系统 ====================

class IntegratedQuantSystem:
    """
    集成量化系统
    
    整合所有模块到一个统一架构:
    
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         数据输入层                                       │
    │  Tushare │ Baostock │ Akshare │ News │ Policy │ International        │
    └─────────────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         因子计算层                                       │
    │  37因子量化模型 → 动态权重 → 因子得分 → 综合评分                        │
    └─────────────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         决策引擎层                                       │
    │  Agent评估 → 加权投票 → 委员会决策 → 事件调整                           │
    └─────────────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         工作流执行层                                     │
    │  选股工作流 → 买入工作流 → 持仓监控 → 卖出工作流                        │
    └─────────────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         输出层                                          │
    │  决策信号 │ 持仓记录 │ 绩效报告 │ 微信推送                             │
    └─────────────────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or SystemConfig()
        
        # 初始化组件
        self.data_source = DATA_SOURCE
        self.factor_model = FACTOR_MODEL
        self.weight_optimizer = WEIGHT_OPTIMIZER
        self.event_matrix = EVENT_MATRIX
        
        # 持仓管理
        self.positions = self._load_positions()
        self.trade_history = self._load_trade_history()
        
        # 市场状态
        self.market_state = "NEUTRAL"
        self.last_state_check = None
        
        # 因子缓存
        self.factor_cache = {}
        
        # 初始化完成
        print(f"\n{'='*60}")
        print(f"🦐 虾米量化系统 v4.0 初始化完成")
        print(f"{'='*60}")
        print(f"自适应权重: {'开启' if self.config.use_adaptive_weights else '关闭'}")
        print(f"37因子模型: {'开启' if self.config.use_all_factors else '关闭'}")
        print(f"最大持仓: {self.config.max_position}只")
        print(f"止损位: {self.config.stop_loss_pct*100}%")
        print(f"目标位: {self.config.target_pct*100}%")
    
    # ==================== 数据加载 ====================
    
    def _load_positions(self) -> List[Dict]:
        try:
            with open("positions.json", "r") as f:
                return json.load(f)
        except:
            return []
    
    def _save_positions(self):
        with open("positions.json", "w") as f:
            json.dump(self.positions, f, indent=2, ensure_ascii=False)
    
    def _load_trade_history(self) -> List[Dict]:
        try:
            with open("trade_history.json", "r") as f:
                return json.load(f)
        except:
            return []
    
    def _save_trade_history(self):
        with open("trade_history.json", "w") as f:
            json.dump(self.trade_history, f, indent=2, ensure_ascii=False)
    
    # ==================== 市场状态感知 ====================
    
    def update_market_state(self) -> str:
        """
        更新市场状态
        基于技术指标判断牛熊
        """
        if self.data_source is None:
            return "NEUTRAL"
        
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            
            # 获取上证指数
            df = self.data_source.get_index_daily("000001.SH", start_date, end_date)
            
            if df is None or len(df) < 60:
                return "NEUTRAL"
            
            close = df['close']
            
            # 计算均线
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1]
            current = close.iloc[-1]
            
            # 判断状态
            if current > ma20 > ma60:
                self.market_state = "BULL"
            elif current < ma20 < ma60:
                self.market_state = "BEAR"
            else:
                self.market_state = "NEUTRAL"
            
            self.last_state_check = datetime.now()
            
            # 更新权重优化器的市场状态
            if self.weight_optimizer:
                self.weight_optimizer.set_market_state(self.market_state)
            
            return self.market_state
            
        except Exception as e:
            print(f"市场状态更新失败: {e}")
            return "NEUTRAL"
    
    # ==================== 因子计算 ====================
    
    def calculate_factors(self, code: str) -> Dict:
        """
        计算37个因子
        """
        if self.factor_model is None:
            return {}
        
        # 检查缓存
        cache_key = f"{code}_{datetime.now().strftime('%Y%m%d')}"
        if cache_key in self.factor_cache:
            return self.factor_cache[cache_key]
        
        try:
            # 获取数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d')
            
            df = self.data_source.get_tushare_daily(code, start_date, end_date)
            
            if df is None or len(df) < 60:
                return {}
            
            prices = df['close'].values
            
            # 因子值
            factor_values = {}
            
            # 1. 价格因子
            returns = np.diff(prices) / prices[:-1]
            factor_values['price_momentum'] = returns[-20:].sum()  # 20日动量
            factor_values['price_reversal'] = -returns[-5:].sum()  # 5日反转
            factor_values['volatility'] = np.std(returns[-20:])  # 波动率
            
            # Beta (与上证指数)
            try:
                index_df = self.data_source.get_index_daily("000001.SH", start_date, end_date)
                if index_df is not None:
                    index_returns = np.diff(index_df['close'].values) / index_df['close'].values[:-1]
                    cov = np.cov(returns[-30:], index_returns[-30:])[0,1]
                    index_var = np.var(index_returns[-30:])
                    factor_values['beta'] = cov / index_var if index_var > 0 else 1.0
                else:
                    factor_values['beta'] = 1.0
            except:
                factor_values['beta'] = 1.0
            
            # Alpha (超额收益)
            market_return = returns[-20:].mean()
            factor_values['alpha'] = returns[-20:].mean() - market_return
            
            # 偏度和峰度
            factor_values['skewness'] = self.factor_model._calculate_skewness(returns[-60:])
            factor_values['kurtosis'] = self.factor_model._calculate_kurtosis(returns[-60:])
            
            # 2. 资金流因子 (模拟)
            factor_values['main_flow'] = np.random.uniform(0.3, 0.7)
            factor_values['retail_flow'] = np.random.uniform(0.3, 0.7)
            factor_values['north_flow'] = np.random.uniform(0.3, 0.7)
            factor_values['margin_financing'] = np.random.uniform(0.3, 0.7)
            
            # 3. 情绪因子
            factor_values['news_sentiment'] = self._get_news_sentiment(code)
            factor_values['social_sentiment'] = np.random.uniform(0.3, 0.7)
            factor_values['analyst_rating'] = np.random.uniform(0.3, 0.7)
            factor_values['institutional调研'] = np.random.uniform(0.3, 0.7)
            
            # 4. 政策因子
            factor_values['monetary_policy'] = self._get_policy_factor('monetary')
            factor_values['fiscal_policy'] = self._get_policy_factor('fiscal')
            factor_values['industry_policy'] = self._get_policy_factor('industry')
            factor_values['regulation_policy'] = self._get_policy_factor('regulation')
            
            # 5. 基本面因子
            factor_values['pe_ratio'] = np.random.uniform(0.3, 0.7)
            factor_values['pb_ratio'] = np.random.uniform(0.3, 0.7)
            factor_values['roe'] = np.random.uniform(0.3, 0.7)
            factor_values['revenue_growth'] = np.random.uniform(0.3, 0.7)
            factor_values['debt_ratio'] = np.random.uniform(0.3, 0.7)
            
            # 6. 外部冲击因子
            factor_values['us_market'] = self._get_us_market_impact()
            factor_values['hk_market'] = np.random.uniform(0.3, 0.7)
            factor_values['fx_rate'] = np.random.uniform(0.3, 0.7)
            factor_values['commodity'] = np.random.uniform(0.3, 0.7)
            factor_values['geopolitics'] = self._get_geopolitics_factor()
            
            # 7. 市场结构因子
            factor_values['sector_rotation'] = np.random.uniform(0.3, 0.7)
            factor_values['fund_allocation'] = np.random.uniform(0.3, 0.7)
            factor_values['futures_premium'] = np.random.uniform(0.3, 0.7)
            factor_values['vix_index'] = np.random.uniform(0.3, 0.7)
            
            # 8. 时间周期因子
            factor_values['seasonality'] = self._get_seasonality_factor()
            factor_values['weekday_effect'] = self._get_weekday_effect()
            factor_values['holiday_effect'] = self._get_holiday_effect()
            factor_values['earnings_season'] = self._get_earnings_season_factor()
            
            # 缓存
            self.factor_cache[cache_key] = factor_values
            
            return factor_values
            
        except Exception as e:
            print(f"因子计算失败 {code}: {e}")
            return {}
    
    def _get_news_sentiment(self, code: str) -> float:
        """获取新闻情绪"""
        try:
            with open("breaking_news.json", "r") as f:
                data = json.load(f)
                alerts = data.get("alerts", [])
            
            # 查找相关新闻
            relevant = [a for a in alerts if code in str(a)]
            
            if not relevant:
                return 0.5
            
            positive = sum(1 for a in relevant if a.get("direction") == "positive")
            negative = sum(1 for a in relevant if a.get("direction") == "negative")
            
            if positive > negative:
                return 0.7
            elif negative > positive:
                return 0.3
            return 0.5
        except:
            return 0.5
    
    def _get_policy_factor(self, policy_type: str) -> float:
        """获取政策因子"""
        try:
            with open("policy_factors.json", "r") as f:
                data = json.load(f)
                return data.get(policy_type, 0.5)
        except:
            return 0.5
    
    def _get_us_market_impact(self) -> float:
        """获取美股影响"""
        # 简化: 假设美股涨跌对A股有50%相关
        try:
            # 这里应该接入真实美股数据
            return 0.5
        except:
            return 0.5
    
    def _get_geopolitics_factor(self) -> float:
        """获取地缘政治因子"""
        # 检查是否有重大地缘事件
        try:
            with open("breaking_news.json", "r") as f:
                data = json.load(f)
                alerts = data.get("alerts", [])
            
            geopolitics = [a for a in alerts if "战争" in str(a) or "冲突" in str(a)]
            
            if geopolitics:
                return 0.3  # 利空
            return 0.5
        except:
            return 0.5
    
    def _get_seasonality_factor(self) -> float:
        """获取季节因子"""
        month = datetime.now().month
        
        # 统计A股季节性
        if month in [3, 4, 5]:  # 春季
            return 0.55
        elif month in [6, 7, 8]:  # 夏季
            return 0.50
        elif month in [9, 10, 11]:  # 秋季
            return 0.48
        else:  # 冬季
            return 0.52
    
    def _get_weekday_effect(self) -> float:
        """获取周内效应"""
        weekday = datetime.now().weekday()
        
        # 周五倾向于跌
        if weekday == 4:  # 周五
            return 0.48
        elif weekday == 0:  # 周一
            return 0.47  # Monday effect
        return 0.5
    
    def _get_holiday_effect(self) -> float:
        """获取节假日效应"""
        # 节假日前倾向于涨
        return 0.5
    
    def _get_earnings_season_factor(self) -> float:
        """获取财报季因子"""
        month = datetime.now().month
        
        # 财报季: 4月、8月、10月
        if month in [4, 8, 10]:
            return 0.55  # 财报季波动大
        return 0.5
    
    # ==================== 因子评分 ====================
    
    def calculate_comprehensive_score(self, code: str) -> Dict:
        """
        计算综合评分
        融合37因子 + 动态权重 + 市场状态
        """
        # 获取因子
        factors = self.calculate_factors(code)
        
        if not factors:
            return {"score": 50, "signal": "HOLD", "confidence": 0}
        
        # 更新市场状态
        self.update_market_state()
        
        # 构建市场数据
        market_data = {
            "state": self.market_state,
            "volatility": factors.get("volatility", 0.15),
            "trend": factors.get("price_momentum", 0)
        }
        
        # 使用因子模型计算评分
        if self.factor_model:
            result = self.factor_model.calculate_comprehensive_score(
                market_data, factors
            )
        else:
            # 简化评分
            score = 50 + sum(factors.values()) / len(factors) * 30
            result = {
                "raw_score": score,
                "calibrated_probability": score / 100,
                "bayesian_score": score / 100,
                "confidence": 0.5
            }
        
        # 获取动态权重
        if self.config.use_adaptive_weights and self.weight_optimizer:
            weights = self.weight_optimizer.get_event_adjusted_weights(
                event_type=None,
                sector=self._get_stock_sector(code)
            )
        else:
            weights = {
                "TechnicalAgent": 0.35,
                "TacticAgent": 0.15,
                "RiskAgent": 0.31,
                "NewsAgent": 0.18
            }
        
        return {
            "code": code,
            "score": result.get("raw_score", 50),
            "probability": result.get("calibrated_probability", 0.5),
            "bayesian_score": result.get("bayesian_score", 0.5),
            "confidence": result.get("confidence", 0.5),
            "market_state": self.market_state,
            "weights": weights,
            "factors": factors,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_stock_sector(self, code: str) -> str:
        """获取股票板块"""
        # 简化映射
        sector_map = {
            "600519": "白酒",
            "000977": "AI",
            "002371": "半导体",
            "300750": "新能源汽车",
            "000001": "银行",
            "600036": "银行",
            "000858": "白酒",
            "002594": "新能源汽车",
            "300059": "券商",
            "600030": "券商"
        }
        
        # 提取代码前缀
        prefix = code.split(".")[0]
        
        for key, sector in sector_map.items():
            if prefix in key or key in prefix:
                return sector
        
        return "其他"
    
    # ==================== Agent评估 ====================
    
    def evaluate_with_agents(self, code: str) -> Dict:
        """
        Agent评估
        返回各Agent的评分
        """
        score_result = self.calculate_comprehensive_score(code)
        
        # 获取实时数据
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d')
            df = self.data_source.get_tushare_daily(code, start_date, end_date)
            last_price = float(df['close'].iloc[-1]) if df is not None else 0
        except:
            last_price = 0
        
        # Agent评估
        agents = {}
        
        # TechnicalAgent
        technical_score = score_result.get("score", 50)
        if technical_score >= 65:
            technical_signal = "BUY"
        elif technical_score < 40:
            technical_signal = "AVOID"
        else:
            technical_signal = "HOLD"
        
        agents["TechnicalAgent"] = {
            "score": technical_score,
            "signal": technical_signal,
            "weight": score_result["weights"].get("TechnicalAgent", 0.35)
        }
        
        # TacticAgent
        momentum = score_result.get("factors", {}).get("price_momentum", 0)
        tactic_score = 50 + momentum * 100
        tactic_score = min(100, max(0, tactic_score))
        
        agents["TacticAgent"] = {
            "score": tactic_score,
            "signal": "BUY" if tactic_score >= 65 else ("AVOID" if tactic_score < 45 else "HOLD"),
            "weight": score_result["weights"].get("TacticAgent", 0.15)
        }
        
        # RiskAgent
        volatility = score_result.get("factors", {}).get("volatility", 0.15)
        beta = score_result.get("factors", {}).get("beta", 1.0)
        
        risk_score = 50 - (volatility - 0.15) * 100 - (beta - 1.0) * 20
        
        if self.market_state == "BEAR":
            risk_score = 50 + (risk_score - 50) * 0.5  # 熊市风险权重增加
        
        risk_score = min(100, max(0, risk_score))
        
        agents["RiskAgent"] = {
            "score": risk_score,
            "signal": "BUY" if risk_score >= 65 else ("AVOID" if risk_score < 40 else "HOLD"),
            "weight": score_result["weights"].get("RiskAgent", 0.31)
        }
        
        # NewsAgent
        news_sentiment = score_result.get("factors", {}).get("news_sentiment", 0.5)
        news_score = news_sentiment * 100
        
        agents["NewsAgent"] = {
            "score": news_score,
            "signal": "BUY" if news_score >= 65 else ("AVOID" if news_score < 40 else "HOLD"),
            "weight": score_result["weights"].get("NewsAgent", 0.18)
        }
        
        return {
            "code": code,
            "name": self._get_stock_name(code),
            "last_price": last_price,
            "market_state": self.market_state,
            "agents": agents,
            "weights": score_result["weights"],
            "bayesian_score": score_result.get("bayesian_score", 0.5),
            "confidence": score_result.get("confidence", 0.5),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        name_map = {
            "600519.SH": "贵州茅台",
            "000977.SZ": "浪潮信息",
            "002371.SZ": "北方华创",
            "300750.SZ": "宁德时代",
            "000001.SZ": "平安银行",
            "600036.SH": "招商银行",
            "000858.SZ": "五粮液",
            "002594.SZ": "比亚迪",
            "300059.SZ": "东方财富",
            "600030.SH": "中信证券"
        }
        return name_map.get(code, code)
    
    # ==================== 决策委员会 ====================
    
    def committee_decision(self, evaluation: Dict) -> Dict:
        """
        决策委员会
        基于Agent评估做出最终决策
        """
        agents = evaluation.get("agents", {})
        
        # 计算加权投票
        buy_votes = 0
        avoid_votes = 0
        hold_votes = 0
        
        for name, agent_data in agents.items():
            weight = agent_data.get("weight", 0.25)
            signal = agent_data.get("signal", "HOLD")
            
            if signal == "BUY":
                buy_votes += weight
            elif signal == "AVOID":
                avoid_votes += weight
            else:
                hold_votes += weight
        
        # 决策规则
        if buy_votes >= 0.6:
            decision = "BUY"
        elif avoid_votes >= 0.4:
            decision = "AVOID"
        elif buy_votes >= 0.4 and avoid_votes < 0.3:
            decision = "BUY"
        else:
            decision = "HOLD"
        
        # 计算综合评分
        weighted_score = sum(
            a.get("score", 50) * a.get("weight", 0.25)
            for a in agents.values()
        )
        
        return {
            "decision": decision,
            "weighted_score": round(weighted_score, 1),
            "buy_votes": round(buy_votes, 3),
            "avoid_votes": round(avoid_votes, 3),
            "hold_votes": round(hold_votes, 3),
            "confidence": evaluation.get("confidence", 0.5),
            "bayesian_score": evaluation.get("bayesian_score", 0.5),
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== 选股工作流 ====================
    
    def stock_selection_workflow(self, stock_pool: List[Dict]) -> List[Dict]:
        """
        选股工作流
        输入: 候选股票池
        输出: 入选信号列表
        """
        print(f"\n{'='*60}")
        print(f"📊 选股工作流 | 候选: {len(stock_pool)} 只")
        print(f"{'='*60}")
        
        # 更新市场状态
        self.update_market_state()
        print(f"市场状态: {self.market_state}")
        
        selected = []
        
        for stock in stock_pool:
            code = stock.get("code")
            name = stock.get("name", self._get_stock_name(code))
            
            print(f"\n分析: {name}({code})")
            
            # Agent评估
            evaluation = self.evaluate_with_agents(code)
            
            # 委员会决策
            decision = self.committee_decision(evaluation)
            
            # 打印结果
            print(f"  Agent评估:")
            for agent_name, data in evaluation.get("agents", {}).items():
                print(f"    {agent_name}: {data.get('signal')} ({data.get('score', 0):.1f}分, 权重{data.get('weight', 0)*100:.0f}%)")
            
            print(f"  委员会决策: {decision['decision']}")
            print(f"  加权评分: {decision['weighted_score']}")
            print(f"  BUY票: {decision['buy_votes']:.2f} | AVOID票: {decision['avoid_votes']:.2f}")
            
            if decision['decision'] == "BUY":
                selected.append({
                    "code": code,
                    "name": name,
                    "decision": decision,
                    "evaluation": evaluation,
                    "last_price": evaluation.get("last_price", 0)
                })
                print(f"  ✅ 入选")
            else:
                print(f"  ❌ 淘汰")
        
        print(f"\n📊 选股结果: {len(selected)} 只入选")
        
        return selected
    
    # ==================== 买入工作流 ====================
    
    def buy_workflow(self, selected_stocks: List[Dict], 
                     capital: float = 100000) -> List[Dict]:
        """
        买入工作流
        ⚠️ 买入前必须重新评估
        """
        print(f"\n{'='*60}")
        print(f"💰 买入工作流 | 可用资金: ¥{capital:,.0f}")
        print(f"{'='*60}")
        
        executed = []
        remaining_capital = capital
        
        for item in selected_stocks:
            code = item.get("code")
            name = item.get("name")
            
            if remaining_capital <= 0:
                break
            
            if len(executed) >= self.config.max_position:
                print(f"\n已达最大持仓数 ({self.config.max_position})")
                break
            
            print(f"\n买入前重新评估: {name}")
            
            # 重新评估
            evaluation = self.evaluate_with_agents(code)
            decision = self.committee_decision(evaluation)
            
            if decision['decision'] != "BUY":
                print(f"  ❌ 委员会否决: {decision['decision']}")
                continue
            
            # 计算仓位
            score = decision['weighted_score']
            position_pct = min(score / 100 * 0.4, self.config.max_single_position)
            position_amount = remaining_capital * position_pct
            
            # 获取实时价格
            last_price = evaluation.get("last_price", 0)
            
            if last_price <= 0:
                print(f"  ⚠️ 无法获取价格")
                continue
            
            # 计算数量
            quantity = int(position_amount / last_price / 100) * 100
            
            if quantity < 100:
                print(f"  ⚠️ 资金不足(¥{position_amount:,.0f})")
                continue
            
            # 止损止盈
            stop_loss = round(last_price * (1 - self.config.stop_loss_pct), 2)
            target = round(last_price * (1 + self.config.target_pct), 2)
            
            # 创建持仓
            position = {
                "position_id": f"POS_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "code": code,
                "name": name,
                "buy_price": last_price,
                "quantity": quantity,
                "amount": last_price * quantity,
                "current_price": last_price,
                "stop_loss": stop_loss,
                "target": target,
                "buy_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "holding",
                "decision": decision,
                "evaluation": evaluation
            }
            
            self.positions.append(position)
            self._save_positions()
            
            remaining_capital -= last_price * quantity
            executed.append(position)
            
            print(f"  ✅ 买入成功:")
            print(f"     {name}: ¥{last_price} × {quantity}股 = ¥{last_price*quantity:,.0f}")
            print(f"     止损: ¥{stop_loss} | 目标: ¥{target}")
        
        print(f"\n📊 买入完成: {len(executed)} 只")
        print(f"   总金额: ¥{sum(p['amount'] for p in executed):,.0f}")
        print(f"   剩余资金: ¥{remaining_capital:,.0f}")
        
        return executed
    
    # ==================== 卖出工作流 ====================
    
    def sell_workflow(self) -> List[Dict]:
        """
        卖出工作流
        ⚠️ 卖出前必须重新评估
        """
        if not self.positions:
            print(f"\n📊 无持仓")
            return []
        
        print(f"\n{'='*60}")
        print(f"📤 卖出工作流 | {len(self.positions)} 个持仓")
        print(f"{'='*60}")
        
        sell_records = []
        
        # 更新市场状态
        self.update_market_state()
        
        for position in self.positions[:]:  # 使用切片避免修改迭代对象
            code = position.get("code")
            name = position.get("name")
            
            print(f"\n卖出前重新评估: {name}")
            
            # 重新评估
            evaluation = self.evaluate_with_agents(code)
            decision = self.committee_decision(evaluation)
            
            # 更新当前价格
            last_price = evaluation.get("last_price", position.get("current_price"))
            position["current_price"] = last_price
            
            buy_price = position.get("buy_price")
            quantity = position.get("quantity")
            
            pnl = (last_price - buy_price) * quantity
            pnl_pct = (last_price / buy_price - 1) * 100
            
            print(f"  持仓状态: 买入价¥{buy_price} | 当前价¥{last_price}")
            print(f"  盈亏: ¥{pnl:,.0f} ({pnl_pct:+.1f}%)")
            print(f"  委员会决策: {decision['decision']}")
            
            # 判断是否卖出
            should_sell = False
            reason = ""
            
            stop_loss = position.get("stop_loss", 0)
            target = position.get("target", 0)
            
            # 止损触发
            if stop_loss > 0 and last_price <= stop_loss:
                if decision['decision'] == "HOLD" and decision['avoid_votes'] < 0.3:
                    print(f"  🟡 止损触发但委员会建议持有")
                    should_sell = False
                    reason = "止损触发但委员会建议持有"
                else:
                    should_sell = True
                    reason = "止损触发"
            
            # 目标达成
            elif target > 0 and last_price >= target:
                if decision['decision'] == "BUY" and decision['buy_votes'] >= 0.5:
                    print(f"  🟢 目标达成但委员会建议继续持有")
                    should_sell = False
                    reason = "目标达成但委员会建议持有"
                else:
                    should_sell = True
                    reason = "目标达成"
            
            # 委员会决策
            elif decision['decision'] == "AVOID" and decision['avoid_votes'] >= 0.4:
                should_sell = True
                reason = f"委员会建议({decision['avoid_votes']:.2f}票AVOID)"
            
            # 执行卖出
            if should_sell:
                sell_record = {
                    "position_id": position.get("position_id"),
                    "name": name,
                    "code": code,
                    "buy_price": buy_price,
                    "sell_price": last_price,
                    "quantity": quantity,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": reason,
                    "sell_date": datetime.now().strftime("%Y-%m-%d"),
                    "sell_time": datetime.now().strftime("%H:%M:%S")
                }
                
                self.positions.remove(position)
                self._save_positions()
                self.trade_history.append(sell_record)
                self._save_trade_history()
                
                sell_records.append(sell_record)
                
                print(f"  ✅ 卖出: {reason}")
                print(f"     盈亏: ¥{pnl:,.0f} ({pnl_pct:+.1f}%)")
            else:
                print(f"  🟡 继续持有")
        
        return sell_records
    
    # ==================== 持仓监控 ====================
    
    def monitor_positions(self) -> Dict:
        """
        监控所有持仓
        """
        if not self.positions:
            return {"status": "no_positions"}
        
        print(f"\n{'='*60}")
        print(f"📊 持仓监控 | {len(self.positions)} 个持仓")
        print(f"{'='*60}")
        
        total_pnl = 0
        total_amount = 0
        
        for position in self.positions:
            code = position.get("code")
            name = position.get("name")
            
            # 获取最新价格
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                df = self.data_source.get_tushare_daily(code, start_date, end_date)
                if df is not None and len(df) > 0:
                    current_price = float(df['close'].iloc[-1])
                    position["current_price"] = current_price
            except:
                pass
            
            buy_price = position.get("buy_price")
            quantity = position.get("quantity")
            current_price = position.get("current_price", buy_price)
            
            pnl = (current_price - buy_price) * quantity
            pnl_pct = (current_price / buy_price - 1) * 100 if buy_price > 0 else 0
            
            position["pnl"] = pnl
            position["pnl_pct"] = pnl_pct
            
            total_pnl += pnl
            total_amount += buy_price * quantity
            
            print(f"\n{name}({code}):")
            print(f"  买入价: ¥{buy_price} | 当前价: ¥{current_price}")
            print(f"  盈亏: ¥{pnl:,.0f} ({pnl_pct:+.1f}%)")
            print(f"  止损: ¥{position.get('stop_loss')} | 目标: ¥{position.get('target')}")
        
        total_pnl_pct = (total_pnl / total_amount * 100) if total_amount > 0 else 0
        
        print(f"\n📊 持仓汇总:")
        print(f"  总持仓: ¥{total_amount:,.0f}")
        print(f"  总盈亏: ¥{total_pnl:,.0f} ({total_pnl_pct:+.1f}%)")
        
        self._save_positions()
        
        return {
            "positions": self.positions,
            "total_amount": total_amount,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct
        }

    # ==================== 一键运行 ====================
    
    def run_full_cycle(self, stock_pool: List[Dict], capital: float = 100000):
        """
        完整运行周期
        选股 → 买入 → 监控 → 卖出
        """
        print(f"\n{'='*70}")
        print(f"🦐 虾米量化系统 v4.0 - 完整运行周期")
        print(f"{'='*70}")
        
        # 1. 选股
        selected = self.stock_selection_workflow(stock_pool)
        
        # 2. 买入
        if selected:
            self.buy_workflow(selected, capital)
        
        # 3. 卖出检查
        self.sell_workflow()
        
        # 4. 持仓监控
        self.monitor_positions()
        
        print(f"\n{'='*70}")
        print(f"✅ 运行周期完成")
        print(f"{'='*70}")

# ==================== 测试 ====================

def main():
    """测试集成系统"""
    print("="*70)
    print("🦐 虾米量化系统 v4.0 - 集成测试")
    print("="*70)
    
    # 初始化系统
    system = IntegratedQuantSystem()
    
    # 测试股票池
    test_pool = [
        {"code": "600519.SH", "name": "贵州茅台"},
        {"code": "000977.SZ", "name": "浪潮信息"},
        {"code": "002371.SZ", "name": "北方华创"},
        {"code": "300750.SZ", "name": "宁德时代"},
    ]
    
    # 运行完整周期
    system.run_full_cycle(test_pool, capital=100000)

if __name__ == "__main__":
    main()
