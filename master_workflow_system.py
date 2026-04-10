#!/usr/bin/env python3
"""
虾米量化系统 - 三大核心工作流 v1.3
Master Workflow System v1.3

核心改进:
- v1.3: 动态权重优化 (基于均值-方差优化)
- 买入前: 决策委员会重新评估(实时数据)
- 卖出前: 决策委员会重新评估(实时数据)
- 集成统一数据源(UnifiedDataSource)
- 真正的实盘准备

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import json
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# ==================== 数据源导入 ====================

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from unified_data_source import UnifiedDataSource
    DATA_SOURCE = UnifiedDataSource()
    print("✅ 数据源初始化成功")
except Exception as e:
    print(f"⚠️ 数据源初始化失败: {e}")
    DATA_SOURCE = None

# ==================== Agent定义 ====================

class TechnicalAgent:
    """技术分析Agent"""
    def __init__(self):
        self.name = "TechnicalAgent"
        self.weight = 0.30
    
    def analyze(self, context: Dict) -> Dict:
        """技术分析"""
        df = context.get("kline_data")
        if df is None or len(df) < 20:
            return {"score": 50, "signal": "HOLD", "reasons": [], "details": {}}
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        # MA
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20
        
        # MACD
        exp12 = close.ewm(span=12).mean()
        exp26 = close.ewm(span=26).mean()
        macd = exp12 - exp26
        macd_signal = macd.ewm(span=9).mean()
        macd_hist = (macd - macd_signal).iloc[-1]
        macd_prev = (macd - macd_signal).iloc[-2] if len(df) >= 2 else 0
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1] if loss.iloc[-1] != 0 else 50
        
        # KDJ
        low_n = low.rolling(9).min()
        high_n = high.rolling(9).max()
        rsv = (close - low_n) / (high_n - low_n) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        j = 3 * k - 2 * d
        k_val = k.iloc[-1] if not k.isna().all() else 50
        d_val = d.iloc[-1] if not d.isna().all() else 50
        j_val = j.iloc[-1] if not j.isna().all() else 50
        
        # 评分
        score = 50
        reasons = []
        details = {
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "rsi": round(rsi, 1),
            "kdj_k": round(k_val, 1),
            "kdj_d": round(d_val, 1),
            "kdj_j": round(j_val, 1),
            "macd_hist": round(macd_hist, 4)
        }
        
        if ma5 > ma20 and ma20 > ma60:
            score += 20
            reasons.append("MA多头排列")
        elif ma5 < ma20 and ma20 < ma60:
            score -= 15
            reasons.append("MA空头排列")
        
        # MACD金叉死叉
        if macd_hist > 0 and macd_prev <= 0:
            score += 15
            reasons.append("MACD金叉")
        elif macd_hist < 0 and macd_prev >= 0:
            score -= 10
            reasons.append("MACD死叉")
        elif macd_hist > 0:
            score += 5
            reasons.append("MACD多头")
        
        # RSI
        if 40 <= rsi <= 60:
            score += 10
            reasons.append(f"RSI健康({rsi:.0f})")
        elif rsi > 70:
            score -= 5
            reasons.append(f"RSI超买({rsi:.0f})")
        elif rsi < 30:
            score += 10
            reasons.append(f"RSI超卖({rsi:.0f})")
        
        # KDJ
        if k_val > d_val and j_val < 80:
            score += 5
            reasons.append("KDJ健康")
        elif j_val > 90:
            score -= 5
            reasons.append("KDJ超买")
        
        score = min(100, max(0, score))
        
        return {
            "score": score,
            "signal": "BUY" if score >= 65 else ("AVOID" if score < 40 else "HOLD"),
            "reasons": reasons,
            "details": details
        }

class TacticAgent:
    """战术Agent"""
    def __init__(self):
        self.name = "TacticAgent"
        self.weight = 0.30
    
    def analyze(self, context: Dict) -> Dict:
        """2560战法"""
        df = context.get("kline_data")
        if df is None:
            return {"score": 50, "signal": "HOLD", "reasons": [], "details": {}}
        
        close = df['close']
        # 处理volume列名兼容 (Tushare用'vol', Baostock用'volume')
        vol_col = 'vol' if 'vol' in df.columns else 'volume'
        volume_data = df[vol_col] if vol_col in df.columns else df['amount']
        
        ma25 = close.rolling(25).mean()
        ma25_prev5 = ma25.iloc[-6] if len(ma25) >= 6 else ma25.iloc[0]
        ma25_up = ma25.iloc[-1] > ma25_prev5
        
        vol_ma5 = volume_data.rolling(5).mean()
        vol_ma60 = volume_data.rolling(60).mean()
        
        vol_now = vol_ma5.iloc[-1]
        vol_prev = vol_ma5.iloc[-2] if len(df) >= 2 else vol_now
        vol_60 = vol_ma60.iloc[-1] if len(df) >= 60 else vol_ma5.mean()
        
        vol_golden = vol_now > vol_60 and vol_prev <= vol_60
        
        # 量比
        vol_ratio = volume_data.iloc[-1] / volume_data.iloc[-5:20].mean() if len(df) >= 20 else 1.5
        
        score = 50
        reasons = []
        details = {
            "ma25_up": ma25_up,
            "vol_golden": vol_golden,
            "vol_ratio": round(vol_ratio, 2)
        }
        
        if ma25_up and vol_golden:
            score += 40
            reasons.append("MA25向上+量能金叉")
        elif vol_golden:
            score += 20
            reasons.append("量能金叉")
        elif ma25_up:
            score += 10
            reasons.append("MA25向上")
        
        if vol_ratio > 1.5:
            score += 10
            reasons.append(f"放量({vol_ratio:.1f}倍)")
        
        if vol_ma5.iloc[-1] < vol_ma60.iloc[-1]:
            score -= 15
            reasons.append("量能死叉")
        
        score = min(100, max(0, score))
        
        return {
            "score": score,
            "signal": "BUY" if score >= 65 else ("AVOID" if score < 45 else "HOLD"),
            "reasons": reasons,
            "details": details
        }

class RiskAgent:
    """风险Agent"""
    def __init__(self):
        self.name = "RiskAgent"
        self.weight = 0.25
        self._load_risk_data()
    
    def _load_risk_data(self):
        try:
            with open("comprehensive_results.json", "r") as f:
                data = json.load(f)
                self.var_data = data.get("var", {})
                self.dd_data = data.get("drawdown", {})
                self.beta_data = data.get("beta", {})
        except:
            self.var_data = {}
            self.dd_data = {}
            self.beta_data = {}
    
    def analyze(self, context: Dict) -> Dict:
        """风险分析"""
        name = context.get("stock_name", "")
        market_state = context.get("market_state", "NEUTRAL")
        
        score = 50
        warnings = []
        details = {}
        
        # VaR
        var_info = self.var_data.get(name, {})
        if var_info:
            var_95 = abs(var_info.get("var_95", 0))
            details["var_95"] = var_95
            if var_95 < 2:
                score += 15
            elif var_95 > 4:
                score -= 20
                warnings.append(f"高VaR({var_95:.1f}%)")
        
        # 回撤
        dd_info = self.dd_data.get(name, {})
        if dd_info:
            max_dd = abs(dd_info.get("max_drawdown_pct", 0))
            details["max_drawdown"] = max_dd
            if max_dd < 15:
                score += 10
            elif max_dd > 25:
                score -= 20
                warnings.append(f"大回撤({max_dd:.1f}%)")
        
        # Beta
        beta_info = self.beta_data.get(name, {})
        if beta_info:
            beta = beta_info.get("beta", 1.0)
            details["beta"] = beta
            if beta < 0.8:
                score += 10
            elif beta > 1.5:
                score -= 10
                warnings.append(f"高Beta({beta})")
        
        # 熊市调整
        if market_state == "BEAR" and score > 50:
            score = 50 + (score - 50) * 0.5
        
        score = min(100, max(0, score))
        
        return {
            "score": score,
            "signal": "BUY" if score >= 65 else ("AVOID" if score < 40 else "HOLD"),
            "warnings": warnings,
            "details": details
        }

class NewsAgent:
    """新闻Agent"""
    def __init__(self):
        self.name = "NewsAgent"
        self.weight = 0.15
    
    def analyze(self, context: Dict) -> Dict:
        """新闻情绪"""
        sector = context.get("sector", "")
        name = context.get("stock_name", "")
        
        score = 50
        news_list = []
        
        try:
            with open("breaking_news.json", "r") as f:
                data = json.load(f)
                alerts = data.get("alerts", [])
                
                for alert in alerts:
                    sectors = alert.get("sectors", [])
                    title = alert.get("title", "")
                    if sector in sectors or name in title:
                        news_list.append(alert)
        except:
            pass
        
        if news_list:
            positive = sum(1 for n in news_list if n.get("direction") == "positive")
            negative = sum(1 for n in news_list if n.get("direction") == "negative")
            
            if positive > negative:
                score = 70
            elif negative > positive:
                score = 30
        
        return {
            "score": score,
            "signal": "BUY" if score >= 65 else ("AVOID" if score < 40 else "HOLD"),
            "news_count": len(news_list),
            "details": {"news": news_list[:3]}
        }

# ==================== 决策委员会 ====================

class DecisionCommittee:
    """
    决策委员会 - 使用动态权重优化
    
    权重基于历史信号数据，使用均值-方差优化计算
    """
    
    def __init__(self):
        self.name = "DecisionCommittee"
        self.agents = [
            TechnicalAgent(),
            TacticAgent(),
            RiskAgent(),
            NewsAgent(),
        ]
        
        # 加载动态权重优化器
        try:
            from dynamic_weight_optimizer import DynamicWeightOptimizer
            self.optimizer = DynamicWeightOptimizer()
            self.weights = self.optimizer.get_weights()
            print(f"✅ 动态权重已加载: {self.weights}")
        except Exception as e:
            print(f"⚠️ 动态权重加载失败: {e}")
            self.optimizer = None
            self.weights = {
                "TechnicalAgent": 0.30,
                "TacticAgent": 0.30,
                "RiskAgent": 0.25,
                "NewsAgent": 0.15
            }
        
        # 更新Agent权重
        self._update_agent_weights()
    
    def _update_agent_weights(self):
        """更新Agent权重"""
        for agent in self.agents:
            agent.weight = self.weights.get(agent.name, 0.25)
    
    def optimize_weights(self):
        """重新优化权重"""
        if self.optimizer:
            self.weights = self.optimizer.optimize()
            self._update_agent_weights()
    
    def record_result(self, agent_signals: Dict[str, int], actual_pnl: float):
        """记录交易结果用于权重优化"""
        if self.optimizer:
            self.optimizer.record_trade_result(agent_signals, actual_pnl)
            self.weights = self.optimizer.get_weights()
            self._update_agent_weights()
    
    def evaluate(self, context: Dict) -> Dict:
        """评估 - 委员会对输入进行实时评估"""
        signals = []
        
        for agent in self.agents:
            try:
                result = agent.analyze(context)
                signals.append({
                    "agent": agent.name,
                    "score": result.get("score", 50),
                    "signal": result.get("signal", "HOLD"),
                    "weight": agent.weight,
                    "reasons": result.get("reasons", []),
                    "details": result.get("details", {})
                })
            except Exception as e:
                print(f"  {agent.name}评估失败: {e}")
                signals.append({
                    "agent": agent.name,
                    "score": 50,
                    "signal": "HOLD",
                    "weight": 0.25,
                    "reasons": [],
                    "details": {}
                })
        
        # 动态加权评分
        weighted_score = sum(s.get("score", 50) * s.get("weight", 0.25) for s in signals)
        
        # 投票 (考虑权重)
        buy_votes = sum(s.get("weight", 0.25) for s in signals if s.get("signal") == "BUY")
        avoid_votes = sum(s.get("weight", 0.25) for s in signals if s.get("signal") == "AVOID")
        
        if buy_votes >= 0.6:  # 60%权重支持
            decision = "BUY"
        elif avoid_votes >= 0.4:  # 40%权重反对
            decision = "AVOID"
        elif buy_votes >= 0.4 and avoid_votes < 0.3:
            decision = "BUY"
        else:
            decision = "HOLD"
        
        # 统计票数
        buy_count = sum(1 for s in signals if s.get("signal") == "BUY")
        avoid_count = sum(1 for s in signals if s.get("signal") == "AVOID")
        
        # 收集理由
        all_reasons = []
        all_warnings = []
        for s in signals:
            all_reasons.extend(s.get("reasons", []))
        
        for s in signals:
            details = s.get("details", {})
            if "warnings" in details:
                all_warnings.extend(details["warnings"])
        
        return {
            "decision": decision,
            "weighted_score": round(weighted_score, 1),
            "buy_count": buy_count,
            "avoid_count": avoid_count,
            "buy_votes": round(buy_votes, 2),
            "avoid_votes": round(avoid_votes, 2),
            "signals": signals,
            "reasons": list(set(all_reasons))[:5],
            "warnings": list(set(all_warnings))[:3],
            "weights_used": {s["agent"]: s["weight"] for s in signals},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# ==================== 持仓管理 ====================

class PositionManager:
    """持仓管理器"""
    
    def __init__(self):
        self.file = "positions.json"
        self.positions = self._load()
    
    def _load(self) -> List[Dict]:
        try:
            with open(self.file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save(self):
        with open(self.file, "w") as f:
            json.dump(self.positions, f, indent=2, ensure_ascii=False)
    
    def add(self, position: Dict):
        self.positions.append(position)
        self.save()
    
    def remove(self, position_id: str):
        self.positions = [p for p in self.positions if p.get("position_id") != position_id]
        self.save()
    
    def get_all(self) -> List[Dict]:
        return self.positions

# ==================== 数据获取 ====================

def get_realtime_data(code: str, days: int = 250) -> Optional[Dict]:
    """获取实时数据"""
    if DATA_SOURCE is None:
        return None
    
    try:
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 获取日线数据
        df = DATA_SOURCE.get_tushare_daily(code, start_date, end_date)
        if df is not None and len(df) > 0:
            return {
                "kline_data": df,
                "last_price": float(df['close'].iloc[-1]),
                "change_pct": float(df['pct_chg'].iloc[-1]) if 'pct_chg' in df.columns else 0
            }
    except Exception as e:
        print(f"获取数据失败: {e}")
    
    return None

def get_market_state() -> str:
    """获取市场状态"""
    if DATA_SOURCE is None:
        return "NEUTRAL"
    
    try:
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d')
        
        # 获取上证指数
        df = DATA_SOURCE.get_index_daily("000001.SH", start_date, end_date)
        if df is not None and len(df) >= 60:
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma60 = df['close'].rolling(60).mean().iloc[-1]
            current = df['close'].iloc[-1]
            
            if current > ma20 > ma60:
                return "BULL"
            elif current < ma20 < ma60:
                return "BEAR"
        return "NEUTRAL"
    except Exception as e:
        print(f"市场状态获取失败: {e}")
        return "NEUTRAL"

# ==================== 选股工作流 ====================

class StockSelectionWorkflow:
    """选股工作流"""
    
    def __init__(self):
        self.committee = DecisionCommittee()
    
    def run(self, stock_pool: List[Dict]) -> List[Dict]:
        """选股工作流"""
        print(f"\n{'='*60}")
        print(f"📊 选股工作流 | 候选: {len(stock_pool)} 只")
        print(f"{'='*60}")
        
        selected = []
        market_state = get_market_state()
        print(f"市场状态: {market_state}")
        
        for stock in stock_pool:
            name = stock.get("name", "")
            code = stock.get("code", "")
            sector = stock.get("sector", "")
            
            # 获取实时数据
            realtime = get_realtime_data(code)
            kline_data = realtime["kline_data"] if realtime else None
            
            context = {
                "stock_name": name,
                "stock_code": code,
                "sector": sector,
                "market_state": market_state,
                "kline_data": kline_data
            }
            
            # 委员会评估
            result = self.committee.evaluate(context)
            
            print(f"\n{name}({code}):")
            print(f"  评分: {result['weighted_score']} | 决策: {result['decision']}")
            print(f"  BUY票: {result['buy_count']} | AVOID票: {result['avoid_count']}")
            if result['reasons']:
                print(f"  理由: {', '.join(result['reasons'][:3])}")
            if result['warnings']:
                print(f"  警告: {', '.join(result['warnings'])}")
            
            if result['decision'] in ["BUY"]:
                selected.append({
                    "stock": stock,
                    "evaluation": result,
                    "realtime": realtime
                })
                print(f"  ✅ 入选")
        
        print(f"\n📊 初选结果: {len(selected)} 只")
        return selected

# ==================== 买入工作流 ====================

class BuyWorkflow:
    """买入工作流"""
    
    def __init__(self):
        self.committee = DecisionCommittee()
        self.position_manager = PositionManager()
    
    def pre_buy_check(self, stock: Dict) -> Dict:
        """买入前检查 - 委员会重新评估"""
        name = stock.get("name", "")
        code = stock.get("code", "")
        sector = stock.get("sector", "")
        
        print(f"\n{'='*60}")
        print(f"💰 买入前委员会评估: {name}")
        print(f"⚠️  盘面已变化,必须重新评估!")
        print(f"{'='*60}")
        
        # 获取实时数据
        realtime = get_realtime_data(code)
        kline_data = realtime["kline_data"] if realtime else None
        last_price = realtime.get("last_price") if realtime else stock.get("last_price")
        
        context = {
            "stock_name": name,
            "stock_code": code,
            "sector": sector,
            "market_state": get_market_state(),
            "kline_data": kline_data
        }
        
        result = self.committee.evaluate(context)
        
        print(f"\n委员会实时评估结果:")
        print(f"  评分: {result['weighted_score']}")
        print(f"  决策: {result['decision']}")
        print(f"  BUY票: {result['buy_count']} | AVOID票: {result['avoid_count']}")
        if result['reasons']:
            print(f"  理由: {', '.join(result['reasons'])}")
        if result['warnings']:
            print(f"  警告: {', '.join(result['warnings'])}")
        
        if last_price:
            print(f"  最新价: ¥{last_price}")
        
        return result
    
    def should_buy(self, stock: Dict) -> bool:
        """是否应该买入"""
        result = self.pre_buy_check(stock)
        
        if result['decision'] == "BUY" and result['buy_count'] >= 2:
            print(f"\n✅ 委员会通过,可以买入")
            return True
        elif result['decision'] == "HOLD":
            print(f"\n🟡 委员会观望,暂不买入")
            return False
        else:
            print(f"\n❌ 委员会否决,不买入")
            return False
    
    def execute_buy(self, stock: Dict, result: Dict, capital: float) -> Optional[Dict]:
        """执行买入"""
        name = stock.get("name", "")
        code = stock.get("code", "")
        
        # 获取实时价格
        realtime = get_realtime_data(code)
        price = realtime.get("last_price") if realtime else stock.get("last_price", 100)
        
        if price is None:
            print("无法获取实时价格")
            return None
        
        # 计算仓位
        score = result['weighted_score']
        position_pct = min(score / 100 * 0.4, 0.25)
        amount = capital * position_pct
        
        quantity = int(amount / price / 100) * 100
        if quantity < 100:
            return None
        
        stop_loss = round(price * 0.92, 2)
        target = round(price * 1.15, 2)
        
        position = {
            "position_id": f"POS_{datetime.now().strftime('%Y%m%d%H%M')}",
            "code": code,
            "name": name,
            "sector": stock.get("sector", ""),
            "buy_price": price,
            "quantity": quantity,
            "amount": price * quantity,
            "current_price": price,
            "pnl": 0,
            "pnl_pct": 0,
            "stop_loss": stop_loss,
            "target": target,
            "buy_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "holding",
            "evaluation": {
                "score": result['weighted_score'],
                "decision": result['decision']
            }
        }
        
        self.position_manager.add(position)
        
        print(f"\n✅ 买入执行:")
        print(f"   {name}: ¥{price} × {quantity}股 = ¥{price*quantity:,.0f}")
        print(f"   止损: ¥{stop_loss} | 目标: ¥{target}")
        
        return position
    
    def run(self, selected_stocks: List[Dict], capital: float = 100000) -> List[Dict]:
        """运行买入工作流"""
        print(f"\n{'='*60}")
        print(f"💰 买入工作流 | 可用资金: ¥{capital:,.0f}")
        print(f"{'='*60}")
        
        executed = []
        
        for item in selected_stocks:
            stock = item["stock"]
            result = item["evaluation"]
            
            # 买入前再次评估
            should_buy = self.should_buy(stock)
            
            if should_buy:
                position = self.execute_buy(stock, result, capital)
                if position:
                    executed.append(position)
                    capital -= position["amount"]
            else:
                print(f"\n❌ 跳过: {stock.get('name')}")
        
        print(f"\n📊 买入完成: {len(executed)} 只")
        return executed

# ==================== 卖出工作流 ====================

class SellWorkflow:
    """卖出工作流"""
    
    def __init__(self):
        self.committee = DecisionCommittee()
        self.position_manager = PositionManager()
    
    def pre_sell_check(self, position: Dict) -> Dict:
        """卖出前检查 - 委员会重新评估"""
        name = position.get("name", "")
        code = position.get("code", "")
        
        print(f"\n{'='*60}")
        print(f"📤 卖出前委员会评估: {name}")
        print(f"⚠️  盘面已变化,必须重新评估!")
        print(f"{'='*60}")
        
        # 获取实时数据
        realtime = get_realtime_data(code)
        kline_data = realtime["kline_data"] if realtime else None
        current_price = realtime.get("last_price") if realtime else position.get("current_price")
        
        context = {
            "stock_name": name,
            "stock_code": code,
            "sector": position.get("sector", ""),
            "market_state": get_market_state(),
            "kline_data": kline_data
        }
        
        result = self.committee.evaluate(context)
        
        buy_price = position.get("buy_price", 0)
        pnl_pct = (current_price / buy_price - 1) * 100 if buy_price > 0 and current_price else 0
        
        print(f"\n持仓状态:")
        print(f"  买入价: ¥{buy_price} | 当前价: ¥{current_price}")
        print(f"  盈亏: {pnl_pct:+.1f}%")
        
        print(f"\n委员会实时评估:")
        print(f"  评分: {result['weighted_score']}")
        print(f"  决策: {result['decision']}")
        print(f"  BUY票: {result['buy_count']} | AVOID票: {result['avoid_count']}")
        
        return result
    
    def should_sell(self, position: Dict) -> tuple:
        """是否应该卖出"""
        result = self.pre_sell_check(position)
        
        current_price = position.get("current_price", 0)
        stop_loss = position.get("stop_loss", 0)
        target = position.get("target", 0)
        
        # 止损触发
        if stop_loss > 0 and current_price <= stop_loss:
            if result['decision'] == "HOLD" and result['avoid_count'] == 0:
                print(f"\n🟡 止损触发但委员会建议持有,继续观望")
                return False, "止损触发但委员会建议持有"
            else:
                print(f"\n✅ 止损触发,委员会同意卖出")
                return True, "止损触发"
        
        # 目标达成
        if target > 0 and current_price >= target:
            if result['decision'] == "BUY" and result['buy_count'] >= 2:
                print(f"\n🟢 目标达成但委员会建议继续持有")
                return False, "目标达成但委员会建议持有"
            else:
                print(f"\n✅ 目标达成,委员会同意卖出")
                return True, "目标达成"
        
        # 委员会决策
        if result['decision'] == "AVOID" and result['avoid_count'] >= 2:
            print(f"\n✅ 委员会建议卖出")
            return True, f"委员会建议({result['avoid_count']}票AVOID)"
        
        if result['decision'] == "HOLD" or result['decision'] == "BUY":
            print(f"\n🟡 委员会建议持有")
            return False, "委员会建议持有"
        
        return False, "条件未触发"
    
    def execute_sell(self, position: Dict, reason: str) -> Dict:
        """执行卖出"""
        buy_price = position.get("buy_price", 0)
        sell_price = position.get("current_price", 0)
        quantity = position.get("quantity", 0)
        
        pnl = (sell_price - buy_price) * quantity
        pnl_pct = (sell_price / buy_price - 1) * 100 if buy_price > 0 else 0
        
        sell_record = {
            "position_id": position.get("position_id"),
            "name": position.get("name", ""),
            "code": position.get("code", ""),
            "buy_price": buy_price,
            "sell_price": sell_price,
            "quantity": quantity,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "reason": reason,
            "sell_date": datetime.now().strftime("%Y-%m-%d"),
            "sell_time": datetime.now().strftime("%H:%M:%S")
        }
        
        self.position_manager.remove(position.get("position_id"))
        
        print(f"\n✅ 卖出执行:")
        print(f"   {position.get('name')}: ¥{sell_price} × {quantity}股")
        print(f"   盈亏: {pnl:+.0f} ({pnl_pct:+.1f}%)")
        print(f"   原因: {reason}")
        
        return sell_record

# ==================== 持仓监控工作流 ====================

class PositionMonitorWorkflow:
    """持仓监控工作流"""
    
    def __init__(self):
        self.sell_workflow = SellWorkflow()
        self.position_manager = PositionManager()
    
    def run(self) -> List[Dict]:
        """监控所有持仓"""
        positions = self.position_manager.get_all()
        
        if not positions:
            print(f"\n📊 无持仓")
            return []
        
        print(f"\n{'='*60}")
        print(f"📊 持仓监控工作流 | {len(positions)} 个持仓")
        print(f"{'='*60}")
        
        # 更新实时价格
        for pos in positions:
            code = pos.get("code", "")
            realtime = get_realtime_data(code)
            if realtime:
                pos["current_price"] = realtime.get("last_price")
                buy_price = pos.get("buy_price", 0)
                if buy_price > 0:
                    pos["pnl"] = (pos["current_price"] - buy_price) * pos.get("quantity", 0)
                    pos["pnl_pct"] = (pos["current_price"] / buy_price - 1) * 100
        
        sell_actions = []
        
        for pos in positions:
            name = pos.get("name", "")
            current = pos.get("current_price", 0)
            pnl = pos.get("pnl_pct", 0)
            
            print(f"\n{name}: ¥{current} ({pnl:+.1f}%)")
            
            should_sell, reason = self.sell_workflow.should_sell(pos)
            
            if should_sell:
                sell_record = self.sell_workflow.execute_sell(pos, reason)
                sell_actions.append(sell_record)
        
        return sell_actions

# ==================== 主程序 ====================

def main():
    print("="*60)
    print("虾米量化系统 - 三大工作流 v1.2")
    print("核心改进: 实时数据 + 委员会动态决策")
    print("="*60)
    
    # 测试选股
    print("\n\n" + "="*60)
    print("1️⃣ 选股工作流测试")
    print("="*60)
    
    selection_wf = StockSelectionWorkflow()
    candidates = [
        {"name": "贵州茅台", "code": "600519.SH", "sector": "白酒"},
        {"name": "北方华创", "code": "002371.SZ", "sector": "半导体"},
        {"name": "浪潮信息", "code": "000977.SZ", "sector": "AI"},
    ]
    selected = selection_wf.run(candidates)
    
    # 测试买入
    if selected:
        print("\n\n" + "="*60)
        print("2️⃣ 买入工作流测试")
        print("="*60)
        
        buy_wf = BuyWorkflow()
        positions = buy_wf.run(selected, capital=100000)
    
    # 测试持仓监控
    print("\n\n" + "="*60)
    print("3️⃣ 持仓监控工作流测试")
    print("="*60)
    
    monitor_wf = PositionMonitorWorkflow()
    sell_actions = monitor_wf.run()
    
    print(f"\n📊 监控完成: {len(sell_actions)} 个卖出")

if __name__ == "__main__":
    main()
