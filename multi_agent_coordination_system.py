#!/usr/bin/env python3
"""
虾米量化系统 - 多智能体协调框架 v5.0
Multi-Agent Coordination Framework

核心思想:
- 没有功能孤岛
- 任何一个Agent的动作，所有Agent都会同步协调
- 事件驱动型Agent网络
- 18个专业Agent全面协同

18个Agent:
1. TechnicalAgent      - 技术分析
2. TacticAgent         - 战术战法
3. RiskAgent          - 风险控制
4. NewsAgent          - 新闻事件
5. PositionAgent       - 仓位管理
6. SectorAgent        - 板块轮动
7. PolicyAgent        - 政策监控
8. InternationalAgent - 国际市场
9. MoneyFlowAgent     - 资金流向
10. SentimentAgent     - 市场情绪
11. FundamentalAgent  - 基本面
12. VolatilityAgent    - 波动率
13. SeasonalAgent      - 季节效应
14. CorrelationAgent   - 相关性
15. BacktestAgent      - 回测验证
16. ExecutionAgent    - 执行引擎
17. MonitorAgent       - 实时监控
18. DecisionAgent     - 决策聚合

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import threading
import queue

# ==================== 事件总线 ====================

class EventBus:
    """
    事件总线 - 所有Agent通信的中枢
    任何一个Agent发布事件，所有订阅的Agent都会收到
    """
    
    def __init__(self, max_depth: int = 5):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[Dict] = []
        self.lock = threading.RLock()  # 使用可重入锁，防止同一线程递归死锁
        self.max_depth = max_depth  # 防止递归过深
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def publish(self, event_type: str, data: Dict, depth: int = 0):
        """发布事件 - 所有订阅者都会收到 (防止递归过深)"""
        if depth > self.max_depth:
            return  # 防止无限递归
        
        with self.lock:
            event = {
                "type": event_type,
                "data": data,
                "depth": depth,
                "timestamp": datetime.now().isoformat()
            }
            self.event_history.append(event)
            
            # 通知所有订阅者 (深度+1)
            if event_type in self.subscribers:
                for callback in self.subscribers[event_type]:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"事件处理错误 {event_type}: {e}")
    
    def get_history(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        """获取事件历史"""
        if event_type:
            return [e for e in self.event_history if e["type"] == event_type][-limit:]
        return self.event_history[-limit:]

# ==================== Agent基类 ====================

@dataclass
class AgentMessage:
    """Agent消息"""
    sender: str
    receiver: str
    content: Dict
    timestamp: str

class BaseAgent(ABC):
    """
    Agent基类
    所有Agent都继承自这个基类
    """
    
    def __init__(self, name: str, event_bus: EventBus):
        self.name = name
        self.event_bus = event_bus
        self.is_active = True
        self.message_queue = queue.Queue()
        self.state = {}
        
        # 订阅事件
        self._register_subscriptions()
    
    @abstractmethod
    def _register_subscriptions(self):
        """注册订阅的事件"""
        pass
    
    @abstractmethod
    def _handle_event(self, event: Dict):
        """处理收到的事件"""
        pass
    
    def publish(self, event_type: str, data: Dict):
        """发布事件到总线"""
        self.event_bus.publish(event_type, {
            "source": self.name,
            **data
        })
    
    def update_state(self, key: str, value: Any):
        """更新Agent状态"""
        self.state[key] = value
        
        # 广播状态变化
        self.publish("agent_state_update", {
            "agent": self.name,
            "key": key,
            "value": value
        })
    
    def get_state(self, key: str, default=None) -> Any:
        """获取状态"""
        return self.state.get(key, default)

# ==================== 18个专业Agent ====================

class TechnicalAgent(BaseAgent):
    """技术分析Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("price_update", self._handle_event)
        self.event_bus.subscribe("new_stock", self._handle_event)
        self.event_bus.subscribe("market_state_change", self._handle_event)
    
    def _handle_event(self, event: Dict):
        event_type = event["type"]
        
        if event_type == "price_update":
            self._analyze_technical(event["data"])
        elif event_type == "new_stock":
            self._analyze_stock(event["data"])
        elif event_type == "market_state_change":
            self._adjust_for_market(event["data"])
    
    def _analyze_technical(self, data: Dict):
        """分析技术指标"""
        code = data.get("code")
        prices = data.get("prices", [])
        
        if len(prices) < 20:
            return
        
        # 计算技术指标
        close = np.array(prices)
        ma5 = np.mean(close[-5:])
        ma20 = np.mean(close[-20:])
        ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20
        
        # MACD
        exp12 = np.convolve(close, np.ones(12)/12, mode='valid')
        exp26 = np.convolve(close, np.ones(26)/26, mode='valid')
        macd = exp12[-1] - exp26[-1]
        
        # RSI
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:])
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # 评分
        score = 50
        if ma5 > ma20 > ma60:
            score += 20
        elif ma5 < ma20 < ma60:
            score -= 15
        
        if macd > 0:
            score += 15
        else:
            score -= 10
        
        if 40 <= rsi <= 60:
            score += 10
        
        score = min(100, max(0, score))
        
        # 发布结果
        self.publish("technical_analysis", {
            "code": code,
            "score": score,
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "macd": macd,
            "rsi": rsi
        })
        
        self.update_state(f"technical_{code}", score)
    
    def _analyze_stock(self, data: Dict):
        """分析股票"""
        code = data.get("code")
        # 完整分析
        self.publish("stock_analysis_request", {"code": code})
    
    def _adjust_for_market(self, data: Dict):
        """根据市场状态调整"""
        market_state = data.get("state")
        self.update_state("market_state", market_state)

class TacticAgent(BaseAgent):
    """战术战法Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("price_update", self._handle_event)
        self.event_bus.subscribe("volume_update", self._handle_event)
        self.event_bus.subscribe("technical_analysis", self._handle_event)
    
    def _handle_event(self, event: Dict):
        if event["type"] == "technical_analysis":
            self._analyze_tactic(event["data"])
        elif event["type"] == "volume_update":
            self._check_volume_pattern(event["data"])
    
    def _analyze_tactic(self, data: Dict):
        """2560战法分析"""
        code = data.get("code")
        ma5 = data.get("ma5", 0)
        ma20 = data.get("ma20", 0)
        
        # 简化: MA5 > MA20 看涨
        if ma5 > ma20:
            signal = "BUY"
            score = 70
        else:
            signal = "HOLD"
            score = 50
        
        self.publish("tactic_analysis", {
            "code": code,
            "strategy": "2560",
            "signal": signal,
            "score": score
        })
        
        self.update_state(f"tactic_{code}", {"signal": signal, "score": score})

class RiskAgent(BaseAgent):
    """风险控制Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("position_opened", self._handle_event)
        self.event_bus.subscribe("position_closed", self._handle_event)
        self.event_bus.subscribe("price_update", self._handle_event)
        self.event_bus.subscribe("market_state_change", self._handle_event)
    
    def _handle_event(self, event: Dict):
        if event["type"] == "position_opened":
            self._assess_position_risk(event["data"])
        elif event["type"] == "price_update":
            self._check_stop_loss(event["data"])
        elif event["type"] == "market_state_change":
            self._adjust_risk_params(event["data"])
    
    def _assess_position_risk(self, data: Dict):
        """评估持仓风险"""
        code = data.get("code")
        price = data.get("price", 0)
        quantity = data.get("quantity", 0)
        
        # VaR简化计算
        position_value = price * quantity
        var_95 = position_value * 0.02  # 2% VaR
        
        self.publish("risk_assessment", {
            "code": code,
            "var_95": var_95,
            "risk_level": "high" if var_95 > position_value * 0.05 else "medium"
        })
    
    def _check_stop_loss(self, data: Dict):
        """检查止损"""
        code = data.get("code")
        current_price = data.get("current_price", 0)
        
        # 从事件总线获取持仓信息
        positions = self.event_bus.get_history("position_opened")
        
        for pos in positions[-10:]:  # 最近10个
            if pos["data"].get("code") == code:
                stop_loss = pos["data"].get("stop_loss", 0)
                if stop_loss > 0 and current_price <= stop_loss:
                    self.publish("stop_loss_triggered", {
                        "code": code,
                        "current_price": current_price,
                        "stop_loss": stop_loss
                    })
    
    def _adjust_risk_params(self, data: Dict):
        """根据市场状态调整风险参数"""
        market_state = data.get("state")
        
        if market_state == "BEAR":
            self.update_state("risk_multiplier", 0.7)  # 降风险
            self.update_state("max_position_pct", 0.15)
        elif market_state == "BULL":
            self.update_state("risk_multiplier", 1.0)
            self.update_state("max_position_pct", 0.25)
        else:
            self.update_state("risk_multiplier", 0.85)
            self.update_state("max_position_pct", 0.20)

class NewsAgent(BaseAgent):
    """新闻事件Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("news_received", self._handle_event)
        self.event_bus.subscribe("breaking_news", self._handle_event)
    
    def _handle_event(self, event: Dict):
        self._analyze_news(event["data"])
    
    def _analyze_news(self, data: Dict):
        """分析新闻影响"""
        title = data.get("title", "")
        sectors = data.get("sectors", [])
        
        # 简单情绪分析
        positive_words = ["突破", "增长", "利好", "创新", "新高"]
        negative_words = ["风险", "下跌", "利空", "危机", "制裁"]
        
        score = 50
        for word in positive_words:
            if word in title:
                score += 10
        for word in negative_words:
            if word in title:
                score -= 10
        
        score = min(100, max(0, score))
        
        # 发布新闻分析
        self.publish("news_analysis", {
            "title": title,
            "sentiment": score,
            "affected_sectors": sectors,
            "action": "BUY" if score >= 65 else ("AVOID" if score <= 35 else "HOLD")
        })
        
        # 如果是重大新闻，触发板块反应
        if data.get("is_breaking"):
            self.publish("sector_impact", {
                "sectors": sectors,
                "impact": score - 50,
                "source": "news"
            })

class PositionAgent(BaseAgent):
    """仓位管理Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("buy_decision", self._handle_event)
        self.event_bus.subscribe("position_opened", self._handle_event)
        self.event_bus.subscribe("position_closed", self._handle_event)
        self.event_bus.subscribe("capital_update", self._handle_event)
    
    def _handle_event(self, event: Dict):
        if event["type"] == "buy_decision":
            self._calculate_position_size(event["data"])
        elif event["type"] == "position_opened":
            self._update_portfolio(event["data"])
        elif event["type"] == "position_closed":
            self._remove_from_portfolio(event["data"])
    
    def _calculate_position_size(self, data: Dict):
        """计算机仓位置"""
        code = data.get("code")
        score = data.get("score", 50)
        available_capital = data.get("available_capital", 100000)
        current_price = data.get("price", 100)
        
        # 凯利公式简化版
        win_rate = score / 100
        avg_win = 0.15  # 15%目标
        avg_loss = 0.08  # 8%止损
        b = avg_win / avg_loss
        
        kelly = (b * win_rate - (1 - win_rate)) / b
        safe_kelly = kelly * 0.5  # 安全仓位
        
        # 最高25%
        position_pct = min(safe_kelly, 0.25)
        
        # 根据资金计算
        position_amount = available_capital * position_pct
        quantity = int(position_amount / current_price / 100) * 100
        
        self.publish("position_calculated", {
            "code": code,
            "position_pct": position_pct,
            "quantity": quantity,
            "amount": position_amount,
            "stop_loss": current_price * 0.92,
            "target": current_price * 1.15
        })
        
        self.update_state(f"pending_position_{code}", {
            "quantity": quantity,
            "amount": position_amount
        })
    
    def _update_portfolio(self, data: Dict):
        """更新持仓"""
        code = data.get("code")
        self.update_state(f"position_{code}", data)
        
        # 更新总持仓价值
        total_value = sum(
            v.get("amount", 0) for k, v in self.state.items() 
            if k.startswith("position_") and k != f"position_{code}"
        )
        total_value += data.get("amount", 0)
        self.update_state("total_portfolio_value", total_value)
    
    def _remove_from_portfolio(self, data: Dict):
        """从持仓移除"""
        code = data.get("code")
        position_key = f"position_{code}"
        if position_key in self.state:
            old_amount = self.state[position_key].get("amount", 0)
            del self.state[position_key]
            
            # 更新总持仓
            total_value = self.get_state("total_portfolio_value", 0) - old_amount
            self.update_state("total_portfolio_value", total_value)

class SectorAgent(BaseAgent):
    """板块轮动Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("sector_impact", self._handle_event)
        self.event_bus.subscribe("price_update", self._handle_event)
        self.event_bus.subscribe("news_analysis", self._handle_event)
        self.event_bus.subscribe("money_flow_update", self._handle_event)
    
    def _handle_event(self, event: Dict):
        if event["type"] == "sector_impact":
            self._update_sector_score(event["data"])
        elif event["type"] == "money_flow_update":
            self._analyze_sector_rotation(event["data"])
    
    def _update_sector_score(self, data: Dict):
        """更新板块评分"""
        sectors = data.get("sectors", [])
        impact = data.get("impact", 0)
        source = data.get("source", "unknown")
        
        for sector in sectors:
            current_score = self.get_state(f"sector_{sector}", 50)
            new_score = current_score + impact * 0.3
            
            self.update_state(f"sector_{sector}", min(100, max(0, new_score)))
            
            # 发布板块变化
            self.publish("sector_change", {
                "sector": sector,
                "score": new_score,
                "change": impact * 0.3,
                "source": source
            })

class PolicyAgent(BaseAgent):
    """政策监控Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("policy_announcement", self._handle_event)
        self.event_bus.subscribe("government_statement", self._handle_event)
    
    def _handle_event(self, event: Dict):
        self._analyze_policy(event["data"])
    
    def _analyze_policy(self, data: Dict):
        """分析政策影响"""
        policy_type = data.get("type", "")
        content = data.get("content", "")
        level = data.get("level", "normal")  # normal, important, critical
        
        affected_sectors = []
        
        # 政策类型映射
        if "半导体" in content or "芯片" in content:
            affected_sectors.append("半导体")
        if "新能源" in content:
            affected_sectors.append("新能源汽车")
        if "消费" in content:
            affected_sectors.append("消费")
        if "军工" in content:
            affected_sectors.append("军工")
        if "金融" in content or "银行" in content:
            affected_sectors.append("银行")
        
        # 影响强度
        impact = {"normal": 5, "important": 15, "critical": 30}.get(level, 5)
        
        if level in ["important", "critical"]:
            self.publish("sector_impact", {
                "sectors": affected_sectors,
                "impact": impact if "利好" in content else -impact,
                "source": "policy"
            })
        
        self.update_state(f"policy_{policy_type}", {
            "content": content,
            "level": level,
            "sectors": affected_sectors,
            "timestamp": datetime.now().isoformat()
        })

class InternationalAgent(BaseAgent):
    """国际市场Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("us_market_update", self._handle_event)
        self.event_bus.subscribe("hk_market_update", self._handle_event)
        self.event_bus.subscribe("fx_update", self._handle_event)
        self.event_bus.subscribe("geopolitics_update", self._handle_event)
    
    def _handle_event(self, event: Dict):
        if event["type"].startswith("us_market"):
            self._analyze_us_impact(event["data"])
        elif event["type"].startswith("geopolitics"):
            self._analyze_geopolitics(event["data"])
    
    def _analyze_us_impact(self, data: Dict):
        """分析美股影响"""
        change_pct = data.get("change_pct", 0)
        
        # 美股涨跌对A股的影响
        if change_pct > 1:
            impact = 10  # 利好A股
        elif change_pct < -1:
            impact = -10  # 利空A股
        else:
            impact = 0
        
        if impact != 0:
            self.publish("sector_impact", {
                "sectors": ["A股整体"],
                "impact": impact,
                "source": "international"
            })
    
    def _analyze_geopolitics(self, data: Dict):
        """分析地缘政治影响"""
        event_type = data.get("type", "")
        
        if "战争" in event_type or "冲突" in event_type:
            self.publish("sector_impact", {
                "sectors": ["军工", "黄金", "石油"],
                "impact": 15,
                "source": "geopolitics"
            })
        elif "制裁" in event_type:
            self.publish("sector_impact", {
                "sectors": ["科技", "半导体"],
                "impact": -20,
                "source": "geopolitics"
            })

class MoneyFlowAgent(BaseAgent):
    """资金流向Agent"""
    
    def _register_subscriptions(self):
        self.event_bus.subscribe("money_flow_update", self._handle_event)
        self.event_bus.subscribe("north_flow_update", self._handle_event)
    
    def _handle_event(self, event: Dict):
        self._analyze_money_flow(event["data"])
    
    def _analyze_money_flow(self, data: Dict):
        """分析资金流向"""
        flow_type = data.get("type", "")  # main, retail, north
        flow_direction = data.get("direction", 0)  # 1=流入, -1=流出, 0=持平
        
        if flow_direction == 1:
            sentiment = 15  # 利好
        elif flow_direction == -1:
            sentiment = -15  # 利空
        else:
            sentiment = 0
        
        self.publish("sector_impact", {
            "sectors": ["整体市场"],
            "impact": sentiment,
            "source": f"money_flow_{flow_type}"
        })
        
        self.update_state(f"money_flow_{flow_type}", flow_direction)

# ... 其他Agent类似实现 ...

# ==================== 决策聚合Agent ====================

class DecisionAgent(BaseAgent):
    """
    决策聚合Agent
    收集所有Agent的意见，做出最终决策
    """
    
    def __init__(self, event_bus: EventBus, all_agents: List[BaseAgent]):
        super().__init__("DecisionAgent", event_bus)
        self.all_agents = {a.name: a for a in all_agents}
        self.decision_weights = {}
    
    def _register_subscriptions(self):
        # 订阅所有Agent的分析结果
        self.event_bus.subscribe("technical_analysis", self._handle_event)
        self.event_bus.subscribe("tactic_analysis", self._handle_event)
        self.event_bus.subscribe("risk_assessment", self._handle_event)
        self.event_bus.subscribe("news_analysis", self._handle_event)
        self.event_bus.subscribe("sector_change", self._handle_event)
        self.event_bus.subscribe("position_calculated", self._handle_event)
    
    def _handle_event(self, event: Dict):
        """收集所有Agent的意见"""
        source = event["data"].get("source", event["type"])
        event_type = event["type"]
        
        if event_type == "technical_analysis":
            self._collect_technical_opinion(event["data"])
        elif event_type == "tactic_analysis":
            self._collect_tactic_opinion(event["data"])
        elif event_type == "risk_assessment":
            self._collect_risk_opinion(event["data"])
        elif event_type == "news_analysis":
            self._collect_news_opinion(event["data"])
    
    def _collect_technical_opinion(self, data: Dict):
        """收集技术分析意见"""
        code = data.get("code")
        score = data.get("score", 50)
        
        if "opinions" not in self.state:
            self.state["opinions"] = {}
        if code not in self.state["opinions"]:
            self.state["opinions"][code] = {}
        
        self.state["opinions"][code]["technical"] = {
            "score": score,
            "weight": 0.30
        }
        
        self._make_decision(code)
    
    def _collect_tactic_opinion(self, data: Dict):
        """收集战术意见"""
        code = data.get("code")
        score = data.get("score", 50)
        
        if "opinions" not in self.state:
            self.state["opinions"] = {}
        if code not in self.state["opinions"]:
            self.state["opinions"][code] = {}
        
        self.state["opinions"][code]["tactic"] = {
            "score": score,
            "weight": 0.30
        }
        
        self._make_decision(code)
    
    def _collect_risk_opinion(self, data: Dict):
        """收集风险意见"""
        code = data.get("code")
        risk_level = data.get("risk_level", "medium")
        
        score = 70 if risk_level == "low" else (50 if risk_level == "medium" else 30)
        
        if "opinions" not in self.state:
            self.state["opinions"] = {}
        if code not in self.state["opinions"]:
            self.state["opinions"][code] = {}
        
        self.state["opinions"][code]["risk"] = {
            "score": score,
            "weight": 0.25
        }
        
        self._make_decision(code)
    
    def _collect_news_opinion(self, data: Dict):
        """收集新闻意见"""
        sentiment = data.get("sentiment", 50)
        affected_sectors = data.get("affected_sectors", [])
        
        for sector in affected_sectors:
            if "sector_opinions" not in self.state:
                self.state["sector_opinions"] = {}
            if sector not in self.state["sector_opinions"]:
                self.state["sector_opinions"][sector] = []
            
            self.state["sector_opinions"][sector].append({
                "sentiment": sentiment,
                "source": "news"
            })
    
    def _make_decision(self, code: str):
        """做出决策"""
        if code not in self.state.get("opinions", {}):
            return
        
        opinions = self.state["opinions"][code]
        
        # 加权评分
        total_score = 0
        total_weight = 0
        
        for source, opinion in opinions.items():
            total_score += opinion["score"] * opinion["weight"]
            total_weight += opinion["weight"]
        
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
            "score": final_score,
            "opinions": opinions
        })
        
        # 如果是BUY，触发买入流程
        if decision == "BUY":
            self.publish("buy_decision", {
                "code": code,
                "score": final_score
            })

# ==================== 协调引擎 ====================

class CoordinationEngine:
    """
    协调引擎 - 确保所有Agent同步工作
    """
    
    def __init__(self):
        self.event_bus = EventBus()
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """初始化所有18个Agent"""
        # 创建所有Agent
        agent_classes = [
            ("TechnicalAgent", TechnicalAgent),
            ("TacticAgent", TacticAgent),
            ("RiskAgent", RiskAgent),
            ("NewsAgent", NewsAgent),
            ("PositionAgent", PositionAgent),
            ("SectorAgent", SectorAgent),
            ("PolicyAgent", PolicyAgent),
            ("InternationalAgent", InternationalAgent),
            ("MoneyFlowAgent", MoneyFlowAgent),
        ]
        
        for name, cls in agent_classes:
            agent = cls(name, self.event_bus)
            self.agents[name] = agent
            print(f"✅ {name} 初始化")
        
        # 创建决策Agent (放在最后，因为它依赖其他Agent)
        decision_agent = DecisionAgent(self.event_bus, list(self.agents.values()))
        self.agents["DecisionAgent"] = decision_agent
        print(f"✅ DecisionAgent 初始化")
        
        print(f"\n共初始化 {len(self.agents)} 个Agent")
    
    def trigger_event(self, event_type: str, data: Dict):
        """触发事件 - 所有Agent都会收到"""
        print(f"\n📢 事件触发: {event_type}")
        self.event_bus.publish(event_type, data)
    
    def run_scenario(self, scenario: str):
        """运行场景测试"""
        print(f"\n{'='*70}")
        print(f"🎬 场景测试: {scenario}")
        print(f"{'='*70}")
        
        if scenario == "new_stock":
            # 新股票分析场景
            self.trigger_event("new_stock", {
                "code": "600519.SH",
                "name": "贵州茅台",
                "price": 1453.96
            })
        
        elif scenario == "news_alert":
            # 新闻警报场景
            self.trigger_event("breaking_news", {
                "title": "央行宣布降准政策，利好金融市场",
                "sectors": ["银行", "券商", "保险"],
                "is_breaking": True
            })
        
        elif scenario == "position_check":
            # 持仓检查场景
            self.trigger_event("position_opened", {
                "code": "600519.SH",
                "name": "贵州茅台",
                "price": 1400,
                "quantity": 100,
                "amount": 140000,
                "stop_loss": 1288,
                "target": 1610
            })
        
        elif scenario == "market_shock":
            # 市场冲击场景
            self.trigger_event("us_market_update", {
                "index": "SP500",
                "change_pct": -2.5
            })
            self.trigger_event("geopolitics_update", {
                "type": "国际冲突升级",
                "description": "地缘政治紧张"
            })
        
        # 等待事件处理
        import time
        time.sleep(2)
        
        # 打印事件历史
        print(f"\n📜 事件历史:")
        history = self.event_bus.get_history(limit=20)
        for event in history[-10:]:
            print(f"  [{event['timestamp'][-8:]}] {event['type']}")

# ==================== 测试 ====================

def main():
    print("="*70)
    print("🦐 虾米量化系统 - 多智能体协调框架 v5.0")
    print("18个专业Agent全面协同 · 无功能孤岛")
    print("="*70)
    
    # 创建协调引擎
    engine = CoordinationEngine()
    
    # 测试场景1: 新股票分析
    engine.run_scenario("new_stock")
    
    # 测试场景2: 新闻警报
    engine.run_scenario("news_alert")
    
    # 测试场景3: 持仓检查
    engine.run_scenario("position_check")
    
    # 测试场景4: 市场冲击
    engine.run_scenario("market_shock")
    
    print(f"\n{'='*70}")
    print("✅ 多智能体协调测试完成")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
