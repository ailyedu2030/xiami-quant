#!/usr/bin/env python3
"""
虾米量化系统 - 政策监控Agent v1.0
Policy Monitor Agent

监控:
1. 国内政策 (国务院/央行/证监会/科技部)
2. 国际事件 (地缘政治/科技/金融)

分析对A股板块的影响

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
from datetime import datetime
from typing import Dict, List

# ==================== 政策映射 ====================

DOMESTIC_POLICY_MAP = {
    # 金融政策
    "降准": {"sectors": ["银行", "券商", "保险"], "direction": "positive"},
    "降息": {"sectors": ["消费", "地产", "券商"], "direction": "positive"},
    "宽松货币政策": {"sectors": ["银行", "金融", "券商"], "direction": "positive"},
    "外汇管理": {"sectors": ["银行", "外汇"], "direction": "neutral"},
    
    # 科技政策
    "半导体": {"sectors": ["半导体", "芯片", "AI"], "direction": "positive"},
    "自主可控": {"sectors": ["半导体", "软件", "AI"], "direction": "positive"},
    "科技保险": {"sectors": ["保险", "科技", "券商"], "direction": "positive"},
    "AI": {"sectors": ["AI", "半导体", "软件"], "direction": "positive"},
    
    # 消费政策
    "消费贷款": {"sectors": ["消费", "零售", "汽车", "家电"], "direction": "positive"},
    "两新": {"sectors": ["新能源", "家电", "汽车"], "direction": "positive"},
    
    # 基建政策
    "特别国债": {"sectors": ["基建", "高端制造", "钢铁"], "direction": "positive"},
    "两重建设": {"sectors": ["基建", "水泥", "机械"], "direction": "positive"},
    
    # 农业政策
    "乡村振兴": {"sectors": ["银行", "农业", "农机"], "direction": "positive"},
    
    # 贸易政策
    "中美磋商": {"sectors": ["出口", "科技", "半导体"], "direction": "positive"},
    "关税": {"sectors": ["出口", "外贸"], "direction": "neutral"},
}

INTERNATIONAL_POLICY_MAP = {
    # 地缘政治
    "战争": {"sectors": ["军工", "石油", "黄金"], "direction": "positive"},
    "冲突": {"sectors": ["军工", "黄金"], "direction": "positive"},
    "制裁": {"sectors": ["科技", "出口"], "direction": "negative"},
    
    # 科技
    "AI突破": {"sectors": ["AI", "半导体", "软件"], "direction": "positive"},
    "芯片禁令": {"sectors": ["半导体", "自主可控"], "direction": "positive"},
    
    # 金融
    "美联储加息": {"sectors": ["银行", "金融"], "direction": "positive"},
    "美联储降息": {"sectors": ["消费", "黄金"], "direction": "positive"},
    
    # 大宗商品
    "原油": {"sectors": ["石油", "化工"], "direction": "positive"},
    "黄金": {"sectors": ["黄金", "珠宝"], "direction": "positive"},
}

# ==================== 政策Agent类 ====================

class PolicyMonitorAgent:
    """
    政策监控Agent
    监控国内外政策，分析对A股的影响
    """
    
    def __init__(self):
        self.domestic_map = DOMESTIC_POLICY_MAP
        self.international_map = INTERNATIONAL_POLICY_MAP
    
    def analyze_domestic_policy(self, policy_text: str) -> Dict:
        """分析国内政策"""
        matched = []
        sectors = []
        
        for keyword, impact in self.domestic_map.items():
            if keyword in policy_text:
                matched.append(keyword)
                for sector in impact["sectors"]:
                    if sector not in sectors:
                        sectors.append({
                            "sector": sector,
                            "direction": impact["direction"]
                        })
        
        return {
            "has_impact": len(matched) > 0,
            "matched_keywords": matched,
            "affected_sectors": sectors,
            "overall_direction": self._calculate_direction(sectors)
        }
    
    def analyze_international_event(self, event_text: str) -> Dict:
        """分析国际事件"""
        matched = []
        sectors = []
        
        text_lower = event_text.lower()
        
        for keyword, impact in self.international_map.items():
            if keyword in event_text or keyword.lower() in text_lower:
                matched.append(keyword)
                for sector in impact["sectors"]:
                    if sector not in sectors:
                        sectors.append({
                            "sector": sector,
                            "direction": impact["direction"]
                        })
        
        return {
            "has_impact": len(matched) > 0,
            "matched_keywords": matched,
            "affected_sectors": sectors,
            "overall_direction": self._calculate_direction(sectors)
        }
    
    def _calculate_direction(self, sectors: List[Dict]) -> str:
        """计算整体方向"""
        if not sectors:
            return "neutral"
        
        positive = sum(1 for s in sectors if s["direction"] == "positive")
        negative = sum(1 for s in sectors if s["direction"] == "negative")
        
        if positive > negative:
            return "positive"
        elif negative > positive:
            return "negative"
        return "neutral"
    
    def generate_report(self, domestic_policies: List[Dict], 
                       international_events: List[Dict]) -> Dict:
        """生成综合报告"""
        
        # 分析国内政策
        domestic_analysis = []
        for policy in domestic_policies:
            analysis = self.analyze_domestic_policy(policy.get("内容", ""))
            if analysis["has_impact"]:
                domestic_analysis.append({
                    **policy,
                    **analysis
                })
        
        # 分析国际事件
        international_analysis = []
        for event in international_events:
            analysis = self.analyze_international_event(event.get("事件", ""))
            if analysis["has_impact"]:
                international_analysis.append({
                    **event,
                    **analysis
                })
        
        # 汇总受影响板块
        sector_scores = {}
        for item in domestic_analysis + international_analysis:
            direction = item.get("overall_direction", "neutral")
            for sector_info in item.get("affected_sectors", []):
                sector = sector_info["sector"]
                if sector not in sector_scores:
                    sector_scores[sector] = {"positive": 0, "negative": 0, "neutral": 0}
                sector_scores[sector][direction] += 1
        
        # 计算板块最终方向
        sector_ranking = []
        for sector, scores in sector_scores.items():
            total = scores["positive"] + scores["negative"] + scores["neutral"]
            if scores["positive"] > scores["negative"]:
                final_direction = "positive"
                confidence = scores["positive"] / total
            elif scores["negative"] > scores["positive"]:
                final_direction = "negative"
                confidence = scores["negative"] / total
            else:
                final_direction = "neutral"
                confidence = 0.5
            
            sector_ranking.append({
                "sector": sector,
                "direction": final_direction,
                "confidence": round(confidence, 2),
                "positive_count": scores["positive"],
                "negative_count": scores["negative"]
            })
        
        # 排序
        sector_ranking.sort(key=lambda x: (x["direction"] == "positive", x["confidence"]), reverse=True)
        
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "domestic_policies_with_impact": domestic_analysis,
            "international_events_with_impact": international_analysis,
            "sector_ranking": sector_ranking,
            "recommendations": self._generate_recommendations(sector_ranking)
        }
    
    def _generate_recommendations(self, sector_ranking: List[Dict]) -> Dict:
        """生成建议"""
        positive_sectors = [s for s in sector_ranking if s["direction"] == "positive"]
        negative_sectors = [s for s in sector_ranking if s["direction"] == "negative"]
        
        return {
            "重点关注": [s["sector"] for s in positive_sectors[:5]],
            "回避": [s["sector"] for s in negative_sectors[:3]],
            "中性观察": [s["sector"] for s in sector_ranking if s["direction"] == "neutral"][:3]
        }

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("政策监控Agent - 国内外政策分析")
    print("="*80)
    
    agent = PolicyMonitorAgent()
    
    # 国内政策
    domestic_policies = [
        {"政策": "央行2026年Q1货币政策例会", "级别": "央行", 
         "内容": "货币政策保持适度宽松，强化逆周期调节"},
        {"政策": "十五五半导体产业政策", "级别": "国家战略",
         "内容": "半导体列为战略核心领域，自主创新突破"},
        {"政策": "超长期特别国债1.3万亿", "级别": "财政部",
         "内容": "支持两重建设和两新工作"},
        {"政策": "消费贷款贴息政策延续", "级别": "国务院",
         "内容": "个人消费贷款财政贴息政策延至2026年底"},
    ]
    
    # 国际事件
    international_events = [
        {"事件": "俄乌战争持续", "类型": "地缘政治"},
        {"事件": "国产AI芯片突破", "类型": "科技"},
        {"事件": "美联储降息分歧", "类型": "金融"},
        {"事件": "全球半导体销售新高", "类型": "科技"},
    ]
    
    # 生成报告
    report = agent.generate_report(domestic_policies, international_events)
    
    print("\n📊 板块机会排名:")
    print("-" * 50)
    for s in report["sector_ranking"]:
        emoji = "🟢" if s["direction"] == "positive" else ("🔴" if s["direction"] == "negative" else "🟡")
        print(f"{emoji} {s['sector']:<10} 置信度:{s['confidence']:.0%} (+{s['positive_count']}/-{s['negative_count']})")
    
    print("\n💡 投资建议:")
    print("-" * 50)
    rec = report["recommendations"]
    print(f"重点关注: {', '.join(rec['重点关注'])}")
    print(f"回避: {', '.join(rec['回避'])}")
    print(f"中性观察: {', '.join(rec['中性观察'])}")
    
    # 保存报告
    with open("policy_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存: policy_analysis_report.json")

if __name__ == "__main__":
    main()
