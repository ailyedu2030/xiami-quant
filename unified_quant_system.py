#!/usr/bin/env python3
"""
虾米量化系统 - 真正统一系统 v5.0
Truly Unified Quantitative System

核心改进:
1. 消除所有功能孤岛
2. Event Bus驱动一切
3. 单一Agent定义
4. 工作流与因子模型闭环
5. 权重实时广播

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# ==================== 事件总线 (核心) ====================

class EventBus:
    """
    事件总线 - 唯一中枢
    所有组件通过这个总线通信
    """
    
    _instance = None  # 单例模式
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[Dict] = []
        self.lock_count = 0  # 防递归计数
        
        # 全局组件引用
        self.data_source = None
        self.factor_model = None
        self.weight_optimizer = None
        self.positions = []
        self.trade_history = []
        
        print("✅ EventBus 初始化 (单例模式)")
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)
    
    def publish(self, event_type: str, data: Dict, depth: int = 0):
        """发布事件"""
        if depth > 10:  # 防递归
            return
        
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "depth": depth
        }
        
        self.event_history.append(event)
        
        # 通知所有订阅者
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"事件处理错误 {event_type}: {e}")
    
    def get_history(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        if event_type:
            return [e for e in self.event_history if e["type"] == event_type][-limit:]
        return self.event_history[-limit:]


# 全局事件总线
EVENT_BUS = EventBus()

# ==================== Agent基类 ====================

class BaseAgent:
    """所有Agent的基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.event_bus = EVENT_BUS
        self.state = {}
    
    def publish(self, event_type: str, data: Dict):
        """发布事件"""
        self.event_bus.publish(event_type, {"source": self.name, **data})
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        self.event_bus.subscribe(event_type, handler)
    
    def update_state(self, key: str, value: Any):
        """更新状态并广播"""
        self.state[key] = value
        self.publish("agent_state_update", {
            "agent": self.name,
            "key": key,
            "value": str(value)[:100]
        })


# ==================== 单一Agent定义 (消除重复) ====================

class TechnicalAgent(BaseAgent):
    """技术分析Agent"""
    
    def __init__(self):
        super().__init__("TechnicalAgent")
        self.subscribe("price_data", self._on_price_data)
        self.subscribe("new_stock_analysis", self._on_new_stock)
        print(f"  ✅ {self.name}")
    
    def _on_price_data(self, event: Dict):
        """处理价格数据"""
        data = event["data"]
        code = data.get("code")
        prices = np.array(data.get("prices", []))
        
        if len(prices) < 20:
            return
        
        # 计算指标
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        ma60 = np.mean(prices[-60:]) if len(prices) >= 60 else ma20
        
        # RSI
        returns = np.diff(prices) / prices[:-1]
        gains = np.where(returns > 0, returns, 0)
        losses = np.where(returns < 0, -returns, 0)
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:])
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
        
        # 评分
        score = 50
        if ma5 > ma20 > ma60:
            score += 25
        elif ma5 < ma20 < ma60:
            score -= 20
        
        if 40 <= rsi <= 60:
            score += 15
        elif rsi > 70:
            score -= 10
        elif rsi < 30:
            score += 15
        
        score = min(100, max(0, score))
        
        self.publish("technical_result", {
            "code": code,
            "score": score,
            "ma5": ma5,
            "ma20": ma20,
            "rsi": rsi
        })
    
    def _on_new_stock(self, event: Dict):
        """分析新股票"""
        code = event["data"].get("code")
        self.publish("request_price_data", {"code": code})


class TacticAgent(BaseAgent):
    """战术战法Agent (2560)"""
    
    def __init__(self):
        super().__init__("TacticAgent")
        self.subscribe("technical_result", self._on_technical)
        self.subscribe("price_data", self._on_price_data)
        print(f"  ✅ {self.name}")
    
    def _on_technical(self, event: Dict):
        """基于技术结果分析"""
        data = event["data"]
        code = data.get("code")
        ma5 = data.get("ma5", 0)
        ma20 = data.get("ma20", 0)
        
        if ma20 > 0 and ma5 > ma20:
            signal = "BUY"
            score = 70
        else:
            signal = "HOLD"
            score = 50
        
        self.publish("tactic_result", {
            "code": code,
            "strategy": "2560",
            "signal": signal,
            "score": score
        })
    
    def _on_price_data(self, event: Dict):
        """直接基于价格分析"""
        data = event["data"]
        code = data.get("code")
        prices = np.array(data.get("prices", []))
        
        if len(prices) < 25:
            return
        
        ma25 = np.mean(prices[-25:])
        ma25_prev = np.mean(prices[-30:-5]) if len(prices) >= 30 else ma25
        
        ma25_up = ma25 > ma25_prev
        
        self.publish("tactic_result", {
            "code": code,
            "strategy": "MA25",
            "signal": "BUY" if ma25_up else "HOLD",
            "score": 70 if ma25_up else 50
        })


class RiskAgent(BaseAgent):
    """风险控制Agent"""
    
    def __init__(self):
        super().__init__("RiskAgent")
        self.subscribe("position_opened", self._on_position_opened)
        self.subscribe("price_data", self._on_price_update)
        self.subscribe("market_state_change", self._on_market_change)
        print(f"  ✅ {self.name}")
    
    def _on_position_opened(self, event: Dict):
        """持仓打开时评估风险"""
        data = event["data"]
        code = data.get("code")
        price = data.get("price", 0)
        quantity = data.get("quantity", 0)
        
        position_value = price * quantity
        
        # 简化的VaR
        var_95 = position_value * 0.02
        
        risk_level = "high" if var_95 > position_value * 0.05 else "medium"
        
        self.publish("risk_assessment", {
            "code": code,
            "var_95": var_95,
            "risk_level": risk_level,
            "position_value": position_value
        })
        
        # 更新市场状态相关的风险参数
        market_state = self.state.get("market_state", "NEUTRAL")
        if market_state == "BEAR":
            self.update_state("risk_multiplier", 0.7)
            self.update_state("max_position_pct", 0.15)
        elif market_state == "BULL":
            self.update_state("risk_multiplier", 1.0)
            self.update_state("max_position_pct", 0.25)
        else:
            self.update_state("risk_multiplier", 0.85)
            self.update_state("max_position_pct", 0.20)
    
    def _on_price_update(self, event: Dict):
        """价格更新时检查止损"""
        data = event["data"]
        code = data.get("code")
        current_price = data.get("current_price", 0)
        
        # 检查是否有持仓
        for pos in self.event_bus.positions:
            if pos.get("code") == code:
                stop_loss = pos.get("stop_loss", 0)
                if stop_loss > 0 and current_price <= stop_loss:
                    self.publish("stop_loss_triggered", {
                        "code": code,
                        "current_price": current_price,
                        "stop_loss": stop_loss
                    })
    
    def _on_market_change(self, event: Dict):
        """市场状态变化时调整风险参数"""
        state = event["data"].get("state", "NEUTRAL")
        self.update_state("market_state", state)


class NewsAgent(BaseAgent):
    """新闻事件Agent"""
    
    def __init__(self):
        super().__init__("NewsAgent")
        self.subscribe("breaking_news", self._on_breaking_news)
        self.subscribe("news_received", self._on_news)
        print(f"  ✅ {self.name}")
    
    def _on_breaking_news(self, event: Dict):
        """处理突发新闻"""
        data = event["data"]
        title = data.get("title", "")
        sectors = data.get("sectors", [])
        
        # 情绪分析
        score = 50
        if "突破" in title or "增长" in title or "利好" in title:
            score = 70
        elif "风险" in title or "下跌" in title or "利空" in title:
            score = 30
        
        self.publish("news_analysis", {
            "title": title,
            "sentiment": score,
            "affected_sectors": sectors,
            "is_breaking": True
        })
        
        # 如果是重大新闻，影响板块
        if data.get("is_breaking"):
            impact = (score - 50) / 10
            for sector in sectors:
                self.publish("sector_impact", {
                    "sector": sector,
                    "impact": impact,
                    "source": "news"
                })
    
    def _on_news(self, event: Dict):
        """处理普通新闻"""
        self._on_breaking_news(event)


class SectorAgent(BaseAgent):
    """板块轮动Agent"""
    
    def __init__(self):
        super().__init__("SectorAgent")
        self.subscribe("sector_impact", self._on_sector_impact)
        self.subscribe("money_flow_update", self._on_money_flow)
        print(f"  ✅ {self.name}")
    
    def _on_sector_impact(self, event: Dict):
        """处理板块影响"""
        data = event["data"]
        sector = data.get("sector", "")
        impact = data.get("impact", 0)
        
        # 更新板块评分
        current = self.state.get(f"sector_{sector}", 50)
        new_score = current + impact * 10
        new_score = min(100, max(0, new_score))
        
        self.update_state(f"sector_{sector}", new_score)
        
        self.publish("sector_change", {
            "sector": sector,
            "score": new_score,
            "change": impact * 10
        })
    
    def _on_money_flow(self, event: Dict):
        """处理资金流向"""
        data = event["data"]
        direction = data.get("direction", 0)
        
        if direction > 0:
            self.publish("sector_impact", {
                "sector": "整体市场",
                "impact": 0.5,
                "source": "money_flow"
            })


class WeightAgent(BaseAgent):
    """动态权重Agent - 核心创新"""
    
    def __init__(self):
        super().__init__("WeightAgent")
        self.subscribe("trade_completed", self._on_trade_completed)
        self.subscribe("market_state_change", self._on_market_change)
        self.subscribe("request_weights", self._on_request_weights)
        
        # 初始权重
        self.weights = {
            "TechnicalAgent": 0.30,
            "TacticAgent": 0.25,
            "RiskAgent": 0.25,
            "NewsAgent": 0.15,
            "SectorAgent": 0.05
        }
        
        self.trade_count = 0
        print(f"  ✅ {self.name}")
    
    def _on_trade_completed(self, event: Dict):
        """交易完成后更新权重"""
        self.trade_count += 1
        
        # 每10笔交易重新优化一次
        if self.trade_count % 10 == 0:
            self._optimize_weights()
    
    def _on_market_change(self, event: Dict):
        """市场状态变化时调整权重"""
        state = event["data"].get("state", "NEUTRAL")
        
        if state == "BEAR":
            # 熊市增加风险权重
            self.weights["RiskAgent"] = min(0.40, self.weights.get("RiskAgent", 0.25) + 0.10)
            self.weights["TechnicalAgent"] = max(0.20, self.weights.get("TechnicalAgent", 0.30) - 0.05)
        elif state == "BULL":
            # 牛市增加技术权重
            self.weights["TechnicalAgent"] = min(0.40, self.weights.get("TechnicalAgent", 0.30) + 0.10)
            self.weights["RiskAgent"] = max(0.20, self.weights.get("RiskAgent", 0.25) - 0.05)
        
        # 广播新权重
        self.publish("weights_updated", {
            "weights": self.weights.copy(),
            "reason": f"市场状态变化: {state}"
        })
    
    def _on_request_weights(self, event: Dict):
        """响应权重请求"""
        self.publish("weights_updated", {
            "weights": self.weights.copy(),
            "timestamp": datetime.now().isoformat()
        })
    
    def _optimize_weights(self):
        """优化权重 - 简化版"""
        # 读取历史表现
        history = self.event_bus.trade_history[-20:]  # 最近20笔
        
        if len(history) < 5:
            return
        
        # 简单优化：提高胜率高的Agent权重
        agent_performance = {}
        for trade in history:
            agent = trade.get("agent", "unknown")
            pnl = trade.get("pnl", 0)
            if agent not in agent_performance:
                agent_performance[agent] = []
            agent_performance[agent].append(pnl)
        
        # 计算每个Agent的平均收益
        for agent, pnls in agent_performance.items():
            if agent in self.weights and len(pnls) > 0:
                avg_pnl = np.mean(pnls)
                if avg_pnl > 0:
                    self.weights[agent] = min(0.40, self.weights[agent] + 0.02)
                else:
                    self.weights[agent] = max(0.10, self.weights[agent] - 0.02)
        
        # 广播更新
        self.publish("weights_updated", {
            "weights": self.weights.copy(),
            "reason": "定期优化"
        })


class DecisionAgent(BaseAgent):
    """决策聚合Agent - 核心"""
    
    def __init__(self):
        super().__init__("DecisionAgent")
        self.opinions = {}  # {code: {agent: score}}
        
        self.subscribe("technical_result", self._collect_opinion)
        self.subscribe("tactic_result", self._collect_opinion)
        self.subscribe("news_analysis", self._collect_opinion)
        self.subscribe("risk_assessment", self._collect_opinion)
        self.subscribe("sector_change", self._collect_opinion)
        self.subscribe("weights_updated", self._on_weights_updated)
        
        self.weights = {
            "TechnicalAgent": 0.30,
            "TacticAgent": 0.25,
            "RiskAgent": 0.25,
            "NewsAgent": 0.15,
            "SectorAgent": 0.05
        }
        
        print(f"  ✅ {self.name}")
    
    def _on_weights_updated(self, event: Dict):
        """接收权重更新"""
        self.weights = event["data"].get("weights", self.weights)
    
    def _collect_opinion(self, event: Dict):
        """收集各Agent意见"""
        data = event["data"]
        code = data.get("code", "unknown")
        source = event["data"].get("source", event["type"].replace("_result", ""))
        
        if code not in self.opinions:
            self.opinions[code] = {}
        
        score = data.get("score", 50)
        self.opinions[code][source] = score
        
        # 如果收集到足够意见，做决策
        if len(self.opinions[code]) >= 3:
            self._make_decision(code)
    
    def _make_decision(self, code: str):
        """做出最终决策"""
        opinions = self.opinions.get(code, {})
        
        # 加权评分
        total_score = 0
        total_weight = 0
        
        for agent, score in opinions.items():
            weight = self.weights.get(agent, 0.20)
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 50
        
        # 决策
        if final_score >= 65:
            decision = "BUY"
        elif final_score <= 40:
            decision = "AVOID"
        else:
            decision = "HOLD"
        
        # 发布决策
        self.publish("final_decision", {
            "code": code,
            "decision": decision,
            "score": round(final_score, 1),
            "opinions": opinions,
            "weights_used": self.weights.copy()
        })
        
        # 清空意见
        if code in self.opinions:
            del self.opinions[code]


class WorkflowAgent(BaseAgent):
    """工作流Agent - 整合三大工作流"""
    
    def __init__(self):
        super().__init__("WorkflowAgent")
        self.subscribe("final_decision", self._on_decision)
        self.subscribe("stop_loss_triggered", self._on_stop_loss)
        print(f"  ✅ {self.name}")
    
    def _on_decision(self, event: Dict):
        """处理决策"""
        data = event["data"]
        code = data.get("code")
        decision = data.get("decision")
        
        if decision == "BUY":
            self._execute_buy(code, data)
        elif decision == "SELL":
            self._execute_sell(code, data)
    
    def _on_stop_loss(self, event: Dict):
        """处理止损触发"""
        data = event["data"]
        code = data.get("code")
        
        # 查找持仓
        for pos in self.event_bus.positions[:]:
            if pos.get("code") == code:
                self.publish("execute_sell", {
                    "code": code,
                    "reason": "止损触发",
                    "price": data.get("current_price", 0),
                    "quantity": pos.get("quantity", 0)
                })
                break
    
    def _execute_buy(self, code: str, decision_data: Dict):
        """执行买入"""
        # 从EventBus获取价格
        price = 100  # 默认价格，应该从DataAgent获取
        
        # 计算仓位
        available_capital = 100000  # 默认资金
        score = decision_data.get("score", 50)
        position_pct = min(score / 100 * 0.4, 0.25)
        amount = available_capital * position_pct
        quantity = int(amount / price / 100) * 100
        
        if quantity >= 100:
            self.publish("position_opened", {
                "code": code,
                "price": price,
                "quantity": quantity,
                "amount": price * quantity,
                "stop_loss": price * 0.92,
                "target": price * 1.15,
                "decision": decision_data
            })
    
    def _execute_sell(self, code: str, decision_data: Dict):
        """执行卖出"""
        for pos in self.event_bus.positions[:]:
            if pos.get("code") == code:
                self.publish("position_closed", {
                    "code": code,
                    "reason": decision_data.get("reason", "决策卖出"),
                    "price": decision_data.get("price", pos.get("current_price")),
                    "quantity": pos.get("quantity", 0)
                })
                break


class DataAgent(BaseAgent):
    """数据Agent - 统一数据接口"""
    
    def __init__(self, data_source=None):
        super().__init__("DataAgent")
        self.data_source = data_source
        self.subscribe("request_price_data", self._on_request_price)
        self.subscribe("request_market_state", self._on_market_state)
        print(f"  ✅ {self.name}")
    
    def _on_request_price(self, event: Dict):
        """响应价格请求"""
        code = event["data"].get("code")
        
        if self.data_source is None:
            return
        
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            
            df = self.data_source.get_tushare_daily(code, start_date, end_date)
            
            if df is not None and len(df) > 0:
                self.publish("price_data", {
                    "code": code,
                    "prices": df['close'].tolist(),
                    "current_price": float(df['close'].iloc[-1])
                })
        except Exception as e:
            print(f"数据获取失败: {e}")
    
    def _on_market_state(self, event: Dict):
        """获取市场状态"""
        if self.data_source is None:
            self.publish("market_state_change", {"state": "NEUTRAL"})
            return
        
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            
            df = self.data_source.get_index_daily("000001.SH", start_date, end_date)
            
            if df is not None and len(df) >= 20:
                ma20 = df['close'].rolling(20).mean().iloc[-1]
                ma60 = df['close'].rolling(60).mean().iloc[-1] if len(df) >= 60 else ma20
                current = df['close'].iloc[-1]
                
                if current > ma20 > ma60:
                    state = "BULL"
                elif current < ma20 < ma60:
                    state = "BEAR"
                else:
                    state = "NEUTRAL"
                
                self.publish("market_state_change", {"state": state})
        except:
            self.publish("market_state_change", {"state": "NEUTRAL"})


# ==================== 统一系统主类 ====================

class UnifiedQuantSystem:
    """
    真正统一的量化系统
    所有组件通过Event Bus连接
    """
    
    def __init__(self, data_source=None):
        print(f"\n{'='*60}")
        print(f"🦐 虾米量化系统 v5.0 - 真正统一版")
        print(f"{'='*60}")
        
        # 初始化EventBus
        self.event_bus = EVENT_BUS
        self.event_bus.data_source = data_source
        
        # 初始化所有Agent
        self.agents = {}
        
        print("\n初始化Agent网络:")
        self.agents["DataAgent"] = DataAgent(data_source)
        self.agents["TechnicalAgent"] = TechnicalAgent()
        self.agents["TacticAgent"] = TacticAgent()
        self.agents["RiskAgent"] = RiskAgent()
        self.agents["NewsAgent"] = NewsAgent()
        self.agents["SectorAgent"] = SectorAgent()
        self.agents["WeightAgent"] = WeightAgent()
        self.agents["DecisionAgent"] = DecisionAgent()
        self.agents["WorkflowAgent"] = WorkflowAgent()
        
        print(f"\n✅ 共初始化 {len(self.agents)} 个Agent")
        print(f"✅ EventBus 驱动所有组件")
    
    def analyze_stock(self, code: str):
        """分析股票 - 触发完整流程"""
        print(f"\n{'='*60}")
        print(f"📊 分析股票: {code}")
        print(f"{'='*60}")
        
        # 1. 请求价格数据
        self.event_bus.publish("new_stock_analysis", {"code": code})
        
        # 2. 请求市场状态
        self.event_bus.publish("request_market_state", {})
    
    def process_news(self, title: str, sectors: List[str], is_breaking: bool = False):
        """处理新闻"""
        print(f"\n{'='*60}")
        print(f"📰 处理新闻: {title}")
        print(f"{'='*60}")
        
        self.event_bus.publish("breaking_news" if is_breaking else "news_received", {
            "title": title,
            "sectors": sectors,
            "is_breaking": is_breaking
        })
    
    def get_event_summary(self) -> Dict:
        """获取事件汇总"""
        history = self.event_bus.get_history(limit=50)
        
        # 统计事件类型
        event_counts = {}
        for e in history:
            t = e["type"]
            event_counts[t] = event_counts.get(t, 0) + 1
        
        return {
            "total_events": len(history),
            "event_counts": event_counts,
            "recent_events": history[-10:]
        }


# ==================== 测试 ====================

def test_unified_system():
    """测试统一系统"""
    print("="*70)
    print("🦐 虾米量化系统 v5.0 - 统一系统测试")
    print("="*70)
    
    # 创建系统
    system = UnifiedQuantSystem()
    
    # 测试1: 分析股票
    print("\n\n" + "="*70)
    print("🧪 测试1: 分析股票")
    print("="*70)
    system.analyze_stock("600519.SH")
    
    # 测试2: 处理新闻
    print("\n\n" + "="*70)
    print("🧪 测试2: 处理突发新闻")
    print("="*70)
    system.process_news("央行宣布降准，利好金融市场", ["银行", "券商"], True)
    
    # 打印事件汇总
    print("\n\n" + "="*70)
    print("📜 事件汇总")
    print("="*70)
    summary = system.get_event_summary()
    print(f"总事件数: {summary['total_events']}")
    print("\n事件类型统计:")
    for event_type, count in summary['event_counts'].items():
        print(f"  {event_type}: {count}")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_unified_system()
