#!/usr/bin/env python3
"""
决策委员会系统
多个委员独立分析 → 交叉辩论 → 共识决策

委员会成员：
1. 趋势委员 - 专注于趋势和技术形态
2. 价值委员 - 专注于估值和安全边际
3. 资金委员 - 专注于资金流向和市场情绪
4. 风控委员 - 专注于风险评估和止损位
5. 轮动委员 - 专注于板块轮动和时机
"""

import json
from datetime import datetime

class CommitteeMember:
    """委员会成员基类"""
    def __init__(self, name, role):
        self.name = name
        self.role = role
        self.vote = None
        self.reasoning = ""
        self.confidence = 0  # 1-10
    
    def analyze(self, data):
        """分析数据并给出意见"""
        raise NotImplementedError
    
    def vote_on(self, decision):
        """对决策投票"""
        raise NotImplementedError
    
    def debate(self, other_member):
        """与其他委员辩论"""
        raise NotImplementedError


class TrendMember(CommitteeMember):
    """趋势委员 - 专注于趋势和技术形态"""
    
    def analyze(self, data):
        """趋势分析"""
        trend_score = 0
        reasons = []
        
        # 均线多头
        if data.get("ma_bullish"):
            trend_score += 40
            reasons.append("均线多头排列，趋势向好")
        elif data.get("ma_partially_bullish"):
            trend_score += 20
            reasons.append("部分均线多头，趋势尚可")
        else:
            reasons.append("均线混乱，趋势不明")
        
        # MACD
        if data.get("macd_bullish"):
            trend_score += 30
            reasons.append("MACD金叉，动能充足")
        elif data.get("macd_neutral"):
            trend_score += 15
            reasons.append("MACD整理中")
        else:
            reasons.append("MACD死叉，下行动能")
        
        # 近期涨幅
        gain_5d = data.get("gain_5d", 0)
        if gain_5d > 5:
            trend_score += 15
            reasons.append(f"5日涨幅{gain_5d:.1f}%，走势强劲")
        elif gain_5d > 0:
            trend_score += 10
            reasons.append(f"5日涨幅{gain_5d:.1f}%，稳步上涨")
        else:
            reasons.append(f"5日下跌{gain_5d:.1f}%，需要观察")
        
        # RSI位置
        rsi = data.get("rsi", 50)
        if 40 <= rsi <= 60:
            trend_score += 15
            reasons.append(f"RSI={rsi}，处于健康区间")
        elif rsi > 70:
            trend_score -= 10
            reasons.append(f"RSI={rsi}，超买风险")
        elif rsi < 30:
            trend_score += 5
            reasons.append(f"RSI={rsi}，可能超卖")
        
        self.confidence = min(10, trend_score // 10)
        self.reasoning = " | ".join(reasons)
        self.vote = "BUY" if trend_score >= 60 else ("HOLD" if trend_score >= 40 else "AVOID")
        
        return {
            "趋势得分": trend_score,
            "投票": self.vote,
            "信心": self.confidence,
            "理由": self.reasoning
        }


class ValueMember(CommitteeMember):
    """价值委员 - 专注于估值和安全边际"""
    
    def analyze(self, data):
        """估值分析"""
        value_score = 0
        reasons = []
        
        # 行业估值（简化）
        sector = data.get("sector", "")
        pe_ratio = data.get("pe", 20)
        
        # 根据行业判断估值
        if sector in ["白酒", "银行"]:
            if pe_ratio < 30:
                value_score += 40
                reasons.append(f"{sector}行业PE={pe_ratio}，估值合理偏低")
            elif pe_ratio < 40:
                value_score += 25
                reasons.append(f"{sector}行业PE={pe_ratio}，估值适中")
            else:
                value_score += 10
                reasons.append(f"{sector}行业PE={pe_ratio}，估值偏高")
        elif sector in ["AI", "半导体", "新能源汽车"]:
            if pe_ratio < 50:
                value_score += 30
                reasons.append(f"成长股PE={pe_ratio}，可接受")
            elif pe_ratio < 80:
                value_score += 15
                reasons.append(f"成长股PE={pe_ratio}，偏高")
            else:
                value_score += 5
                reasons.append(f"成长股PE={pe_ratio}，估值偏高")
        else:
            value_score += 25
            reasons.append("估值需具体分析")
        
        # 机构评级
        rating = data.get("institution_rating", "中性")
        if rating == "强烈推荐":
            value_score += 30
            reasons.append("机构强烈推荐")
        elif rating == "推荐":
            value_score += 20
            reasons.append("机构推荐")
        elif rating == "中性":
            value_score += 10
            reasons.append("机构中性")
        else:
            reasons.append("机构谨慎")
        
        # 增持/评级上调
        if data.get("rating_upgraded"):
            value_score += 20
            reasons.append("近期评级上调")
        
        # 高股息
        dividend = data.get("dividend_yield", 0)
        if dividend > 3:
            value_score += 15
            reasons.append(f"股息率{dividend:.1f}%，提供安全边际")
        elif dividend > 1:
            value_score += 8
            reasons.append(f"股息率{dividend:.1f}%")
        
        self.confidence = min(10, value_score // 10)
        self.reasoning = " | ".join(reasons)
        self.vote = "BUY" if value_score >= 60 else ("HOLD" if value_score >= 40 else "AVOID")
        
        return {
            "价值得分": value_score,
            "投票": self.vote,
            "信心": self.confidence,
            "理由": self.reasoning
        }


class CapitalMember(CommitteeMember):
    """资金委员 - 专注于资金流向和市场情绪"""
    
    def analyze(self, data):
        """资金面分析"""
        capital_score = 0
        reasons = []
        
        # 成交量
        vol_ratio = data.get("vol_ratio", 1)
        if vol_ratio > 1.5:
            capital_score += 35
            reasons.append(f"成交量放大{vol_ratio:.1f}倍，资金关注")
        elif vol_ratio > 1.2:
            capital_score += 25
            reasons.append(f"成交量放大{vol_ratio:.1f}倍")
        elif vol_ratio < 0.8:
            capital_score += 5
            reasons.append("成交量萎缩，活跃度低")
        else:
            capital_score += 15
            reasons.append("成交量正常")
        
        # 北向资金（简化）
        north_capital = data.get("north_capital_flow", 0)
        if north_capital > 5:
            capital_score += 30
            reasons.append(f"北向净买入{north_capital}亿")
        elif north_capital > 0:
            capital_score += 15
            reasons.append("北向小幅净买入")
        elif north_capital < -5:
            capital_score -= 20
            reasons.append("北向净卖出较多")
        else:
            reasons.append("北向持平")
        
        # 主力资金
        main_capital = data.get("main_capital", 0)
        if main_capital > 3:
            capital_score += 25
            reasons.append("主力资金净流入")
        elif main_capital > 0:
            capital_score += 10
            reasons.append("主力资金小幅流入")
        else:
            capital_score -= 10
            reasons.append("主力资金净流出")
        
        # 股东人数变化（筹码集中度）
        shareholders_change = data.get("shareholders_change", 0)
        if shareholders_change < -5:
            capital_score += 10
            reasons.append("股东人数减少，筹码集中")
        elif shareholders_change > 5:
            capital_score -= 10
            reasons.append("股东人数增加，筹码分散")
        
        self.confidence = min(10, abs(capital_score) // 8)
        self.reasoning = " | ".join(reasons)
        self.vote = "BUY" if capital_score >= 60 else ("HOLD" if capital_score >= 30 else "AVOID")
        
        return {
            "资金得分": capital_score,
            "投票": self.vote,
            "信心": self.confidence,
            "理由": self.reasoning
        }


class RiskMember(CommitteeMember):
    """风控委员 - 专注于风险评估和止损位"""
    
    def analyze(self, data):
        """风险分析"""
        risk_score = 100  # 分数越高越安全
        reasons = []
        
        # RSI风险
        rsi = data.get("rsi", 50)
        if rsi > 80:
            risk_score -= 30
            reasons.append(f"RSI={rsi}严重超买，回调风险高")
        elif rsi > 70:
            risk_score -= 20
            reasons.append(f"RSI={rsi}超买，注意回调")
        elif rsi < 20:
            risk_score -= 15
            reasons.append(f"RSI={rsi}严重超卖")
        
        # 近期涨幅风险
        gain_5d = data.get("gain_5d", 0)
        if gain_5d > 15:
            risk_score -= 25
            reasons.append(f"5日涨幅{gain_5d:.1f}%，短期涨幅过大")
        elif gain_5d > 10:
            risk_score -= 15
            reasons.append(f"5日涨幅{gain_5d:.1f}%，注意回吐压力")
        
        # 波动率风险
        volatility = data.get("volatility", 0)
        if volatility > 5:
            risk_score -= 15
            reasons.append(f"波动率{volatility}%较高")
        
        # 解禁风险
        if data.get("unlock_ratio", 0) > 10:
            risk_score -= 20
            reasons.append(f"解禁比例{data.get('unlock_ratio')}%，供给压力大")
        
        # 大股东减持
        if data.get("major_shareholder_reduce"):
            risk_score -= 25
            reasons.append("大股东减持中")
        
        # 计算止损位
        current_price = data.get("price", 0)
        if current_price > 0:
            if volatility and volatility > 2:
                stop_loss = current_price * (1 - volatility / 100 * 2)
            else:
                stop_loss = current_price * 0.92  # 默认8%止损
            stop_loss_pct = (1 - stop_loss / current_price) * 100
        else:
            stop_loss = 0
            stop_loss_pct = 8
        
        self.confidence = risk_score // 10
        self.reasoning = " | ".join(reasons) + f" | 建议止损位: {stop_loss:.2f}元({stop_loss_pct:.0f}%)"
        self.vote = "BUY" if risk_score >= 70 else ("HOLD" if risk_score >= 50 else "AVOID")
        
        return {
            "风险评分": risk_score,
            "投票": self.vote,
            "信心": self.confidence,
            "止损位": f"{stop_loss:.2f}元",
            "止损比例": f"{stop_loss_pct:.0f}%",
            "理由": self.reasoning
        }


class RotationMember(CommitteeMember):
    """轮动委员 - 专注于板块轮动和时机"""
    
    def analyze(self, data):
        """轮动分析"""
        rotation_score = 50
        reasons = []
        
        # 板块热度
        sector_hotness = data.get("sector_hotness", 3)  # 1-5
        if sector_hotness >= 4:
            rotation_score += 25
            reasons.append(f"所属板块热度{sector_hotness}，资金追捧")
        elif sector_hotness >= 3:
            rotation_score += 15
            reasons.append(f"所属板块热度{sector_hotness}，关注度一般")
        else:
            rotation_score -= 10
            reasons.append(f"所属板块热度{sector_hotness}，关注度低")
        
        # 板块轮动阶段
        rotation_stage = data.get("rotation_stage", "中期")
        if rotation_stage == "初期":
            rotation_score += 20
            reasons.append("板块轮动初期，上涨空间大")
        elif rotation_stage == "中期":
            rotation_score += 10
            reasons.append("板块轮动中期，稳健持有")
        elif rotation_stage == "后期":
            rotation_score -= 15
            reasons.append("板块轮动后期，注意止盈")
        
        # 龙头股表现
        if data.get("is_leader"):
            rotation_score += 15
            reasons.append("行业龙头，资金首选")
        
        # 催化剂
        catalysts = data.get("catalysts", [])
        if catalysts:
            rotation_score += len(catalysts) * 8
            reasons.append(f"有催化因素: {', '.join(catalysts)}")
        
        # 机构调研
        if data.get("recent_research"):
            rotation_score += 10
            reasons.append("近期有机构调研")
        
        self.confidence = min(10, rotation_score // 10)
        self.reasoning = " | ".join(reasons)
        self.vote = "BUY" if rotation_score >= 65 else ("HOLD" if rotation_score >= 45 else "AVOID")
        
        return {
            "轮动得分": rotation_score,
            "投票": self.vote,
            "信心": self.confidence,
            "理由": self.reasoning
        }


class DecisionCommittee:
    """决策委员会"""
    
    def __init__(self):
        self.members = [
            TrendMember("趋势委员", "专注技术形态和趋势"),
            ValueMember("价值委员", "专注估值和安全边际"),
            CapitalMember("资金委员", "专注资金流向"),
            RiskMember("风控委员", "专注风险控制"),
            RotationMember("轮动委员", "专注板块轮动时机")
        ]
        self.individual_votes = {}
        self.consensus = None
        self.min_votes_needed = 3  # 至少3票通过
    
    def conduct_meeting(self, stock_data):
        """召开决策会议"""
        print("\n" + "="*70)
        print(f"  🏛️ 决策委员会会议")
        print(f"  股票: {stock_data.get('name', 'N/A')} ({stock_data.get('code', 'N/A')})")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*70)
        
        self.individual_votes = {}
        
        # 各委员独立分析
        for member in self.members:
            result = member.analyze(stock_data)
            self.individual_votes[member.name] = {
                "投票": result.get("投票"),
                "得分": max(result.values()) if isinstance(result, dict) else 0,
                "理由": result.get("理由", ""),
                "信心": result.get("信心", 5)
            }
            
            print(f"\n📋 {member.name} ({member.role})")
            print(f"   投票: {result.get('投票')} | 信心: {result.get('信心')}/10")
            print(f"   理由: {result.get('理由', 'N/A')}")
        
        # 统计投票
        votes = [self.individual_votes[m.name]["投票"] for m in self.members]
        buy_votes = votes.count("BUY")
        hold_votes = votes.count("HOLD")
        avoid_votes = votes.count("AVOID")
        
        print("\n" + "-"*70)
        print(f"📊 投票统计: 买入={buy_votes} | 持有={hold_votes} | 回避={avoid_votes}")
        
        # 决策
        if buy_votes >= self.min_votes_needed:
            self.consensus = "BUY"
            decision_text = "✅ 建议买入"
        elif buy_votes + hold_votes >= self.min_votes_needed:
            self.consensus = "HOLD"
            decision_text = "⏸️ 建议持有"
        else:
            self.consensus = "AVOID"
            decision_text = "❌ 建议回避"
        
        # 计算综合评分
        total_score = 0
        total_weight = 0
        for member in self.members:
            conf = self.individual_votes[member.name]["信心"]
            score = self.individual_votes[member.name]["得分"]
            total_score += score * conf
            total_weight += conf
        
        composite_score = total_score / total_weight if total_weight > 0 else 50
        
        print(f"\n🏛️ 委员会决策: {decision_text}")
        print(f"📈 综合评分: {composite_score:.0f}/100")
        
        # 获取风控委员的止损建议
        risk_data = self.individual_votes.get("风控委员", {})
        stop_loss = "待定"
        stop_loss_pct = "8%"
        if "止损位" in str(risk_data.get("理由", "")):
            # 提取止损位信息
            for m in self.members:
                if isinstance(m, RiskMember):
                    for k, v in m.analyze(stock_data).items():
                        if "止损" in str(k) or "止损" in str(v):
                            if "止损位" == k:
                                stop_loss = v
                            if "止损比例" == k:
                                stop_loss_pct = v
        
        print(f"🛡️ 止损建议: {stop_loss} ({stop_loss_pct})")
        
        return {
            "决策": self.consensus,
            "综合评分": round(composite_score, 1),
            "买入票数": buy_votes,
            "持有票数": hold_votes,
            "回避票数": avoid_votes,
            "止损位": stop_loss,
            "止损比例": stop_loss_pct,
            "各委员意见": self.individual_votes
        }


def run_committee_decision(stock_data):
    """运行决策委员会"""
    committee = DecisionCommittee()
    result = committee.conduct_meeting(stock_data)
    return result


if __name__ == "__main__":
    # 测试
    test_data = {
        "code": "600519",
        "name": "贵州茅台",
        "sector": "白酒",
        "price": 1460.0,
        "rsi": 52,
        "ma_bullish": True,
        "macd_bullish": True,
        "macd_neutral": False,
        "gain_5d": 3.5,
        "gain_20d": 4.3,
        "vol_ratio": 0.86,
        "pe": 28,
        "dividend_yield": 2.5,
        "institution_rating": "强烈推荐",
        "rating_upgraded": False,
        "north_capital_flow": 2,
        "main_capital": 1,
        "shareholders_change": -3,
        "volatility": 2.5,
        "unlock_ratio": 0,
        "major_shareholder_reduce": False,
        "sector_hotness": 3,
        "rotation_stage": "中期",
        "is_leader": True,
        "catalysts": ["业绩增长", "品牌溢价"],
        "recent_research": True
    }
    
    result = run_committee_decision(test_data)
    print("\n" + "="*70)
    print(f"最终决策: {result['决策']}")
    print("="*70)
