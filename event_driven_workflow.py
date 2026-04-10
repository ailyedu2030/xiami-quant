#!/usr/bin/env python3
"""
虾米量化系统 - 事件驱动工作流引擎 v1.0
Event-Driven Workflow Engine

自动化工作流:
新闻事件 → 自动触发 → 专业分析 → 决策委员会 → 微信推送

设计原则:
1. 事件驱动 - 新闻自动触发工作流
2. 管道式处理 - 每个环节自动串联
3. 决策自动化 - 不需要人工干预

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# ==================== 事件定义 ====================

class EventType(Enum):
    """事件类型"""
    NEWS_INTL = "news_intl"        # 国际新闻
    NEWS_DOMESTIC = "news_domestic"  # 国内政策
    NEWS_MARKET = "news_market"     # 市场新闻
    PRICE_ALERT = "price_alert"     # 价格异动
    SYSTEM_SIGNAL = "system_signal" # 系统信号

class EventSeverity(Enum):
    """事件严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Event:
    """事件"""
    event_type: str
    title: str
    content: str
    source: str
    timestamp: str
    severity: str
    sectors: List[str]
    direction: str  # positive/negative/neutral

# ==================== 分析结果 ====================

@dataclass
class AnalysisResult:
    """分析结果"""
    event: Event
    sentiment_score: float  # 情绪评分 0-100
    sector_impact: Dict[str, float]  # 板块影响评分
    affected_stocks: List[str]  # 受影响股票
    recommendation: str  # 操作建议
    confidence: float  # 置信度

@dataclass
class Decision:
    """决策"""
    decision_id: str
    timestamp: str
    event: Event
    analysis: AnalysisResult
    action: str  # BUY/HOLD/AVOID/ALERT
    stocks: List[str]
    position: str  # 建议仓位
    stop_loss: str  # 止损位
    reason: List[str]
    priority: str  # urgent/normal/low

# ==================== 工作流引擎 ====================

class WorkflowEngine:
    """
    事件驱动工作流引擎
    
    工作流程:
    1. Event Ingestion (事件摄入)
    2. Event Classification (事件分类)
    3. Impact Analysis (影响分析)
    4. Decision Making (决策)
    5. Action Execution (执行)
    """
    
    def __init__(self):
        self.name = "WorkflowEngine"
        self.subscribers = []
        self.event_queue = []
        self.decisions = []
        
        # 加载板块映射
        self.sector_stocks = self._load_sector_stocks()
        self.policy_impact_map = self._load_policy_impact_map()
        
        print(f"✅ {self.name} 初始化完成")
    
    def _load_sector_stocks(self) -> Dict:
        """加载板块-股票映射"""
        return {
            "半导体": ["北方华创", "中微公司", "万华化学"],
            "AI": ["浪潮信息", "科大讯飞"],
            "军工": ["航天电器", "航发动力"],
            "新能源": ["宁德时代", "比亚迪", "恩捷股份"],
            "医药": ["恒瑞医药", "药明康德", "迈瑞医疗"],
            "白酒": ["贵州茅台"],
            "银行": ["招商银行"],
        }
    
    def _load_policy_impact_map(self) -> Dict:
        """加载政策影响映射"""
        return {
            "降准": {"sectors": ["银行", "券商"], "direction": "positive"},
            "降息": {"sectors": ["消费", "地产"], "direction": "positive"},
            "宽松": {"sectors": ["银行", "金融"], "direction": "positive"},
            "半导体": {"sectors": ["半导体", "芯片", "AI"], "direction": "positive"},
            "AI": {"sectors": ["AI", "软件"], "direction": "positive"},
            "军工": {"sectors": ["军工", "无人机"], "direction": "positive"},
            "新能源": {"sectors": ["新能源", "光伏"], "direction": "positive"},
            "俄乌": {"sectors": ["军工", "石油", "黄金"], "direction": "positive"},
            "美联储": {"sectors": ["银行", "金融"], "direction": "neutral"},
            "制裁": {"sectors": ["科技", "出口"], "direction": "negative"},
        }
    
    # ============ 事件摄入 ============
    
    def ingest_event(self, event_data: Dict) -> Event:
        """
        摄入事件
        自动分类和评估
        """
        event = Event(
            event_type=event_data.get("type", "unknown"),
            title=event_data.get("title", ""),
            content=event_data.get("content", ""),
            source=event_data.get("source", ""),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            severity=self._assess_severity(event_data),
            sectors=self._extract_sectors(event_data),
            direction=self._assess_direction(event_data)
        )
        
        self.event_queue.append(event)
        print(f"📥 事件摄入: {event.title[:40]}...")
        
        return event
    
    def _assess_severity(self, event_data: Dict) -> str:
        """评估严重程度"""
        title = event_data.get("title", "").lower()
        content = event_data.get("content", "").lower()
        text = title + content
        
        # 关键词判断
        critical_keywords = ["战争", "暴跌", "暴涨", "制裁", "突破", "革命性"]
        high_keywords = ["政策", "央行", "证监会", "重大", "利好", "利空"]
        
        for kw in critical_keywords:
            if kw in text:
                return EventSeverity.CRITICAL.value
        
        for kw in high_keywords:
            if kw in text:
                return EventSeverity.HIGH.value
        
        return EventSeverity.MEDIUM.value
    
    def _extract_sectors(self, event_data: Dict) -> List[str]:
        """提取相关板块"""
        title = event_data.get("title", "")
        content = event_data.get("content", "")
        text = title + content
        
        sectors = []
        for keyword, info in self.policy_impact_map.items():
            if keyword in text:
                for sector in info["sectors"]:
                    if sector not in sectors:
                        sectors.append(sector)
        
        return sectors[:5]  # 最多5个板块
    
    def _assess_direction(self, event_data: Dict) -> str:
        """评估方向"""
        title = event_data.get("title", "").lower()
        content = event_data.get("content", "").lower()
        text = title + content
        
        positive_keywords = ["利好", "突破", "增长", "大涨", "创新高", "超预期", "积极"]
        negative_keywords = ["利空", "暴跌", "大跌", "风险", "制裁", "衰退"]
        
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
    
    # ============ 影响分析 ============
    
    def analyze_event(self, event: Event) -> AnalysisResult:
        """
        分析事件影响
        """
        print(f"🔍 分析事件: {event.title[:40]}...")
        
        # 情绪评分
        sentiment_score = 50
        if event.direction == "positive":
            sentiment_score = 70
        elif event.direction == "negative":
            sentiment_score = 30
        
        if event.severity == EventSeverity.CRITICAL.value:
            sentiment_score = 85 if event.direction == "positive" else 15
        
        # 板块影响评分
        sector_impact = {}
        for sector in event.sectors:
            impact = 50
            if event.direction == "positive":
                impact = 70 if event.severity in [EventSeverity.HIGH.value, EventSeverity.CRITICAL.value] else 60
            elif event.direction == "negative":
                impact = 30 if event.severity in [EventSeverity.HIGH.value, EventSeverity.CRITICAL.value] else 40
            sector_impact[sector] = impact
        
        # 受影响股票
        affected_stocks = []
        for sector in event.sectors:
            if sector in self.sector_stocks:
                affected_stocks.extend(self.sector_stocks[sector])
        affected_stocks = list(set(affected_stocks))[:5]
        
        # 建议
        if sentiment_score >= 70:
            recommendation = "关注买入机会"
        elif sentiment_score <= 30:
            recommendation = "注意回避风险"
        else:
            recommendation = "保持观察"
        
        result = AnalysisResult(
            event=event,
            sentiment_score=sentiment_score,
            sector_impact=sector_impact,
            affected_stocks=affected_stocks,
            recommendation=recommendation,
            confidence=0.8 if event.severity in [EventSeverity.HIGH.value, EventSeverity.CRITICAL.value] else 0.6
        )
        
        print(f"   情绪评分: {sentiment_score}")
        print(f"   影响板块: {', '.join(event.sectors)}")
        print(f"   建议: {recommendation}")
        
        return result
    
    # ============ 决策 ============
    
    def make_decision(self, analysis: AnalysisResult) -> Decision:
        """
        决策
        """
        event = analysis.event
        
        # 判断操作
        if analysis.sentiment_score >= 75:
            action = "BUY"
        elif analysis.sentiment_score >= 60:
            action = "ALERT"  # 关注但不买入
        elif analysis.sentiment_score <= 30:
            action = "AVOID"
        else:
            action = "HOLD"
        
        # 仓位建议
        if action == "BUY":
            position = "10-20%"
        elif action == "ALERT":
            position = "5-10%"
        elif action == "AVOID":
            position = "0%"
        else:
            position = "维持"
        
        decision = Decision(
            decision_id=f"DEC_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event=event,
            analysis=analysis,
            action=action,
            stocks=analysis.affected_stocks[:3],
            position=position,
            stop_loss="-8%" if action in ["BUY", "ALERT"] else "N/A",
            reason=[
                f"事件: {event.title[:30]}...",
                f"情绪: {analysis.sentiment_score}",
                f"板块: {', '.join(event.sectors[:3])}",
            ],
            priority="urgent" if event.severity in [EventSeverity.HIGH.value, EventSeverity.CRITICAL.value] else "normal"
        )
        
        self.decisions.append(decision)
        
        print(f"📋 决策: {action} | 仓位: {position} | 股票: {', '.join(decision.stocks)}")
        
        return decision
    
    # ============ 执行 ============
    
    def execute_decision(self, decision: Decision) -> Dict:
        """
        执行决策 - 输出推送格式
        """
        action_emoji = "🟢" if decision.action == "BUY" else \
                       ("🔴" if decision.action == "AVOID" else \
                       ("🟡" if decision.action == "ALERT" else "⚪"))
        
        push_message = f"""
{action_emoji} 【{decision.action}】{decision.event.title[:40]}...

📊 事件分析:
   情绪评分: {decision.analysis.sentiment_score}/100
   影响板块: {', '.join(decision.event.sectors)}
   受影响股票: {', '.join(decision.stocks)}
   方向: {decision.event.direction}

📋 操作建议:
   行动: {decision.action}
   仓位: {decision.position}
   止损: {decision.stop_loss}

⏰ 时间: {decision.timestamp}
🔖 决策ID: {decision.decision_id}
"""
        
        # 保存到推送队列
        push_queue_file = "push_queue.json"
        push_queue = []
        if os.path.exists(push_queue_file):
            with open(push_queue_file, 'r') as f:
                push_queue = json.load(f)
        
        push_queue.append({
            "decision": asdict(decision),
            "message": push_message,
            "status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(push_queue_file, 'w') as f:
            json.dump(push_queue, f, ensure_ascii=False, indent=2)
        
        print(f"📤 推送已加入队列")
        
        return {"status": "queued", "message": push_message}
    
    # ============ 主工作流 ============
    
    def process_event(self, event_data: Dict) -> Decision:
        """
        完整工作流: 事件 → 分析 → 决策 → 推送
        """
        print(f"\n{'='*60}")
        print(f"📥 收到新事件: {event_data.get('title', '')[:40]}...")
        print(f"{'='*60}")
        
        # 1. 事件摄入
        event = self.ingest_event(event_data)
        
        # 2. 仅处理中高严重程度事件
        if event.severity in [EventSeverity.LOW.value]:
            print("⚪ 事件严重程度低，跳过详细分析")
            return None
        
        # 3. 影响分析
        analysis = self.analyze_event(event)
        
        # 4. 决策
        decision = self.make_decision(analysis)
        
        # 5. 执行
        result = self.execute_decision(decision)
        
        return decision

# ==================== 新闻触发器 ====================

class NewsTrigger:
    """
    新闻触发器
    监控新闻文件变化，自动触发工作流
    """
    
    def __init__(self, workflow: WorkflowEngine):
        self.workflow = workflow
        self.last_check_file = "last_news_check.json"
    
    def check_for_new_news(self):
        """
        检查新新闻
        由cron定时调用
        """
        print(f"\n🔔 检查新新闻... {datetime.now().strftime('%H:%M:%S')}")
        
        news_file = "breaking_news.json"
        
        if not os.path.exists(news_file):
            print("   无新闻文件")
            return []
        
        try:
            with open(news_file, 'r') as f:
                data = json.load(f)
            
            alerts = data.get("alerts", [])
            print(f"   发现 {len(alerts)} 条新闻")
            
            new_decisions = []
            for alert in alerts:
                # 转换为事件格式
                event_data = {
                    "type": "news",
                    "title": alert.get("title", alert.get("事件", "")),
                    "content": alert.get("content", alert.get("内容", "")),
                    "source": alert.get("source", "未知"),
                    "sectors": alert.get("sectors", []),
                    "direction": alert.get("direction", "neutral")
                }
                
                # 处理事件
                decision = self.workflow.process_event(event_data)
                if decision:
                    new_decisions.append(decision)
            
            return new_decisions
        
        except Exception as e:
            print(f"   检查失败: {e}")
            return []
    
    def save_last_check(self):
        """保存检查时间"""
        with open(self.last_check_file, 'w') as f:
            json.dump({"last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("虾米量化系统 - 事件驱动工作流引擎")
    print("="*80)
    
    # 初始化工作流
    workflow = WorkflowEngine()
    trigger = NewsTrigger(workflow)
    
    # 模拟新闻事件
    test_events = [
        {
            "type": "news_intl",
            "title": "国产AI芯片实现重大突破，性能超预期",
            "content": "某国产AI芯片在训练性能上实现重大突破，达到国际领先水平",
            "source": "新浪财经",
            "keywords": ["AI", "芯片", "突破"]
        },
        {
            "type": "news_domestic",
            "title": "央行宣布定向降准，支持科技创新",
            "content": "央行宣布对科技创新企业实施定向降准政策",
            "source": "央行官网",
            "keywords": ["央行", "降准", "科技"]
        },
        {
            "type": "news_intl",
            "title": "俄乌战场传来新消息",
            "content": "俄乌冲突持续，双方在多个方向激烈交战",
            "source": "网易军事",
            "keywords": ["俄乌", "战争"]
        }
    ]
    
    print("\n" + "="*60)
    print("测试工作流")
    print("="*60)
    
    for event_data in test_events:
        decision = workflow.process_event(event_data)
        if decision:
            print(f"\n📤 推送内容:")
            print(decision.reason)
    
    print("\n" + "="*60)
    print("✅ 工作流测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
