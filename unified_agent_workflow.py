#!/usr/bin/env python3
"""
虾米量化系统 - 统一Agent工作流引擎 v1.0
Unified Agent Workflow Engine

设计原则:
1. 统一Agent输出格式
2. 统一触发机制
3. 整合最新研究权重
4. 完整工作流闭环

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import pandas as pd
import numpy as np
import json
import baostock as bs
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# ==================== 枚举定义 ====================

class Signal(Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    AVOID = "AVOID"

class Confidence(Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"

class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"

# ==================== 统一输出格式 ====================

@dataclass
class SignalResult:
    """所有Agent的统一输出格式"""
    agent_name: str
    signal: str           # BUY/HOLD/AVOID
    score: float          # 0-100
    confidence: str       # HIGH/MED/LOW
    reason: List[str]    # 支持理由
    warning: List[str]    # 风险提示
    data: Dict[str, Any] # Agent特定数据
    
    def to_dict(self) -> dict:
        return asdict(self)

# ==================== 基础Agent类 ====================

class BaseAgent:
    """所有Agent的基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def analyze(self, code: str, name: str, df: pd.DataFrame,
                market_state: MarketRegime, 
                context: Dict) -> SignalResult:
        """
        分析接口 - 所有Agent必须实现
        
        Args:
            code: 股票代码
            name: 股票名称
            df: K线数据 (包含close/high/low/volume/pctChg)
            market_state: 当前市场状态
            context: 共享上下文 (包含权重、Beta等)
        
        Returns:
            SignalResult: 统一格式的信号
        """
        raise NotImplementedError
    
    def _to_signal(self, score: float, threshold_high: float = 70, 
                   threshold_low: float = 40) -> str:
        """分数转信号"""
        if score >= threshold_high:
            return Signal.BUY.value
        elif score >= threshold_low:
            return Signal.HOLD.value
        else:
            return Signal.AVOID.value
    
    def _to_confidence(self, score_diff: float) -> str:
        """置信度"""
        if score_diff > 20:
            return Confidence.HIGH.value
        elif score_diff > 10:
            return Confidence.MED.value
        else:
            return Confidence.LOW.value

# ==================== Agent 1: 技术面Agent ====================

class TechnicalAgent(BaseAgent):
    """技术面分析Agent"""
    
    def __init__(self):
        super().__init__("TechnicalAgent")
    
    def analyze(self, code: str, name: str, df: pd.DataFrame,
                market_state: MarketRegime, context: Dict) -> SignalResult:
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        reasons = []
        warnings = []
        score = 50
        data = {}
        
        # 1. 趋势判断 (MA)
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        if ma5 > ma20 > ma60:
            score += 20
            reasons.append("均线多头排列")
        elif ma5 < ma20 < ma60:
            score -= 15
            warnings.append("均线空头排列")
        else:
            score += 0
            reasons.append("均线纠缠")
        
        data['ma_trend'] = 'bullish' if ma5 > ma20 else 'bearish'
        
        # 2. MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd.iloc[-1] - signal.iloc[-1]
        
        if macd_hist > 0:
            score += 15
            reasons.append("MACD金叉")
        else:
            score -= 10
            warnings.append("MACD死叉")
        
        data['macd_hist'] = float(macd_hist)
        
        # 3. RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        if 40 <= rsi <= 60:
            score += 10
            reasons.append(f"RSI健康({rsi:.1f})")
        elif rsi > 70:
            warnings.append(f"RSI超买({rsi:.1f})")
            score -= 5
        elif rsi < 30:
            reasons.append(f"RSI超卖({rsi:.1f})")
            score += 10
        
        data['rsi'] = float(rsi)
        
        # 4. 成交量趋势
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ma20 = volume.rolling(20).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma20 if vol_ma20 > 0 else 1
        
        if vol_ratio > 1.5:
            score += 10
            reasons.append(f"放量({vol_ratio:.1f}x)")
        elif vol_ratio < 0.7:
            score -= 5
            warnings.append("缩量")
        
        data['vol_ratio'] = float(vol_ratio)
        
        # 5. 市场状态调整
        if market_state == MarketRegime.BEAR:
            if score > 60:
                score = 60  # 熊市降低预期
            warnings.append("熊市环境")
        elif market_state == MarketRegime.BULL:
            if score < 50:
                score = 50  # 牛市提高预期
        
        signal = self._to_signal(score)
        confidence = self._to_confidence(abs(score - 50))
        
        return SignalResult(
            agent_name=self.name,
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reason=reasons,
            warning=warnings,
            data=data
        )

# ==================== Agent 2: 战术Agent (2560) ====================

class Tactic2560Agent(BaseAgent):
    """2560战法Agent"""
    
    def __init__(self):
        super().__init__("Tactic2560Agent")
    
    def analyze(self, code: str, name: str, df: pd.DataFrame,
                market_state: MarketRegime, context: Dict) -> SignalResult:
        
        close = df['close']
        volume = df['volume']
        
        reasons = []
        warnings = []
        score = 50
        data = {}
        
        # MA25趋势
        ma25 = close.rolling(25).mean()
        ma25_trend = ma25.iloc[-1] - ma25.iloc[-5]
        ma25_up = ma25_trend > 0
        
        # VOL_MA5 和 VOL_MA60
        vol_ma5 = volume.rolling(5).mean()
        vol_ma60 = volume.rolling(60).mean()
        
        # 金叉检测
        vol_now = vol_ma5.iloc[-1]
        vol_prev = vol_ma5.iloc[-2]
        vol_60_now = vol_ma60.iloc[-1]
        vol_60_prev = vol_ma60.iloc[-2]
        
        vol_golden = (vol_now > vol_60_now) and (vol_prev <= vol_60_prev)
        vol_dead = (vol_now < vol_60_now) and (vol_prev >= vol_60_prev)
        
        # 买入信号
        if ma25_up and vol_golden:
            score += 40
            reasons.append("MA25向上+量能金叉")
        elif vol_golden:
            score += 20
            reasons.append("量能金叉")
        elif ma25_up:
            score += 10
            reasons.append("MA25向上")
        
        # 卖出信号
        if vol_dead:
            score -= 20
            warnings.append("量能死叉")
        if not ma25_up and score > 50:
            score -= 15
            warnings.append("MA25向下")
        
        # 使用优化后的权重调整
        weights = context.get('weights', {})
        if weights.get('vol_breakout', 0) > 0.5:
            # 放量突破权重高时
            if vol_golden:
                score += 10
        
        data['ma25_up'] = ma25_up
        data['vol_golden'] = vol_golden
        data['vol_dead'] = vol_dead
        
        signal = self._to_signal(score, threshold_high=65, threshold_low=45)
        confidence = self._to_confidence(abs(score - 50))
        
        return SignalResult(
            agent_name=self.name,
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reason=reasons,
            warning=warnings,
            data=data
        )

# ==================== Agent 3: 风险Agent ====================

class RiskAgent(BaseAgent):
    """风险分析Agent"""
    
    def __init__(self):
        super().__init__("RiskAgent")
        # 从研究结果加载风险数据
        self._load_risk_data()
    
    def _load_risk_data(self):
        """加载预计算的风险数据"""
        try:
            with open('/Users/jackie/.openclaw/workspace/stock-research/comprehensive_results.json', 'r') as f:
                data = json.load(f)
                self.risk_data = data.get('var', {})
                self.drawdown_data = data.get('drawdown', {})
        except:
            self.risk_data = {}
            self.drawdown_data = {}
    
    def analyze(self, code: str, name: str, df: pd.DataFrame,
                market_state: MarketRegime, context: Dict) -> SignalResult:
        
        reasons = []
        warnings = []
        score = 50
        data = {}
        
        # 从预加载数据查找
        stock_var = self.risk_data.get(name, {})
        stock_dd = self.drawdown_data.get(name, {})
        
        if stock_var:
            var_95 = stock_var.get('var95', 0)
            max_loss = stock_var.get('max_loss', 0)
            risk_level = stock_var.get('risk', '低风险')
            
            # VaR评分
            if abs(var_95) < 2:
                score += 15
                reasons.append(f"VaR低({var_95}%)")
            elif abs(var_95) > 4:
                score -= 20
                warnings.append(f"VaR高({var_95}%)")
            
            data['var_95'] = var_95
            data['risk_level'] = risk_level
        
        if stock_dd:
            max_dd = stock_dd.get('max_drawdown_pct', 0)
            
            if abs(max_dd) < 15:
                score += 10
                reasons.append(f"回撤小({max_dd:.1f}%)")
            elif abs(max_dd) > 25:
                score -= 20
                warnings.append(f"回撤大({max_dd:.1f}%)")
            
            data['max_drawdown'] = max_dd
        
        # Beta评分 (从context获取)
        beta = context.get('beta', {}).get(name, {})
        if beta:
            beta_val = beta.get('beta', 1.0)
            if beta_val < 0.8:
                score += 10
                reasons.append(f"低Beta({beta_val})")
            elif beta_val > 1.5:
                score -= 10
                warnings.append(f"高Beta({beta_val})")
            
            data['beta'] = beta_val
        
        # 熊市调整
        if market_state == MarketRegime.BEAR:
            if score > 50:
                score = 50 + (score - 50) * 0.5  # 降低高风险股票分数
        
        signal = self._to_signal(score, threshold_high=65, threshold_low=40)
        confidence = self._to_confidence(abs(score - 50))
        
        return SignalResult(
            agent_name=self.name,
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reason=reasons,
            warning=warnings,
            data=data
        )

# ==================== Agent 4: 仓位Agent ====================

class PositionAgent(BaseAgent):
    """仓位计算Agent"""
    
    def __init__(self):
        super().__init__("PositionAgent")
    
    def analyze(self, code: str, name: str, df: pd.DataFrame,
                market_state: MarketRegime, context: Dict) -> SignalResult:
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        reasons = []
        warnings = []
        score = 50
        data = {}
        
        # ATR计算
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = atr / close.iloc[-1] * 100 if close.iloc[-1] > 0 else 0
        
        # 止损位
        stop_loss = close.iloc[-1] - 2 * atr
        
        # 凯利仓位
        win_rate = context.get('win_rate', 0.5)
        avg_win = context.get('avg_win', 1)
        avg_loss = context.get('avg_loss', 1)
        
        if avg_loss > 0:
            b = avg_win / avg_loss
            p = win_rate
            kelly = (p * b - (1 - p)) / b if b != 0 else 0
            safe_kelly = kelly * 0.5
            max_pos = min(safe_kelly, 0.25)
        else:
            kelly = 0
            max_pos = 0.1
        
        # 熊市降低仓位
        if market_state == MarketRegime.BEAR:
            max_pos *= 0.7
            warnings.append("熊市降低仓位")
        
        data['atr_pct'] = float(atr_pct)
        data['stop_loss'] = float(stop_loss)
        data['kelly'] = float(kelly)
        data['max_position'] = float(max_pos)
        data['recommended_position'] = f"{min(25, int(max_pos * 100))}%"
        
        if max_pos >= 0.2:
            score += 15
            reasons.append(f"建议仓位{int(max_pos*100)}%")
        elif max_pos >= 0.1:
            score += 5
            reasons.append(f"建议仓位{int(max_pos*100)}%")
        else:
            score -= 10
            warnings.append("建议轻仓")
        
        signal = self._to_signal(score, threshold_high=60, threshold_low=40)
        confidence = self._to_confidence(abs(max_pos - 0.15))
        
        return SignalResult(
            agent_name=self.name,
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reason=reasons,
            warning=warnings,
            data=data
        )

# ==================== 决策引擎 ====================

class DecisionEngine:
    """决策引擎 - 整合所有Agent信号"""
    
    def __init__(self):
        self.agents = [
            TechnicalAgent(),
            Tactic2560Agent(),
            RiskAgent(),
            PositionAgent(),
        ]
        
        # 从研究加载的优化权重
        self._load_optimized_weights()
    
    def _load_optimized_weights(self):
        """加载优化后的权重"""
        try:
            with open('/Users/jackie/.openclaw/workspace/stock-research/optimal_weights_6month.json', 'r') as f:
                data = json.load(f)
                self.weights = data.get('best_weights', {})
        except:
            self.weights = {
                'vol_breakout': 0.705,
                'ma_golden': 0.197,
                'rise_3pct': 0.059,
                'shrink': 0.040,
            }
    
    def decide(self, code: str, name: str, df: pd.DataFrame,
              market_state: MarketRegime, context: Dict) -> Dict:
        """
        综合所有Agent信号做出决策
        """
        # 1. 并行执行所有Agent
        signals = []
        for agent in self.agents:
            try:
                result = agent.analyze(code, name, df, market_state, context)
                signals.append(result)
            except Exception as e:
                print(f"Agent {agent.name} error: {e}")
        
        # 2. 加权评分
        weighted_score = 0
        agent_weights = {
            'TechnicalAgent': 0.30,
            'Tactic2560Agent': 0.30,
            'RiskAgent': 0.25,
            'PositionAgent': 0.15,
        }
        
        for sig in signals:
            weight = agent_weights.get(sig.agent_name, 0.2)
            weighted_score += sig.score * weight
        
        # 3. 综合信号
        buy_count = sum(1 for s in signals if s.signal == Signal.BUY.value)
        avoid_count = sum(1 for s in signals if s.signal == Signal.AVOID.value)
        
        if buy_count >= 3:
            final_signal = Signal.BUY.value
        elif avoid_count >= 2:
            final_signal = Signal.AVOID.value
        else:
            final_signal = Signal.HOLD.value
        
        # 4. 收集理由和警告
        all_reasons = []
        all_warnings = []
        for sig in signals:
            all_reasons.extend(sig.reason)
            all_warnings.extend(sig.warning)
        
        # 5. 获取仓位建议
        position_sig = next((s for s in signals if s.agent_name == 'PositionAgent'), None)
        position = position_sig.data.get('recommended_position', '10%') if position_sig else '10%'
        stop_loss = position_sig.data.get('stop_loss', 0) if position_sig else 0
        
        return {
            'code': code,
            'name': name,
            'signal': final_signal,
            'score': round(weighted_score, 1),
            'confidence': max(s.confidence for s in signals),
            'buy_count': buy_count,
            'reasons': list(set(all_reasons)),
            'warnings': list(set(all_warnings)),
            'position': position,
            'stop_loss': round(stop_loss, 2) if stop_loss else None,
            'agent_signals': [s.to_dict() for s in signals],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# ==================== 主工作流 ====================

class TradingWorkflow:
    """交易工作流"""
    
    def __init__(self):
        self.engine = DecisionEngine()
        self.bs = None
    
    def connect(self):
        """连接数据源"""
        self.bs = bs.login()
    
    def disconnect(self):
        """断开连接"""
        if self.bs:
            bs.logout()
    
    def get_market_state(self, index_code: str = 'sh.000001') -> MarketRegime:
        """判断市场状态"""
        rs = bs.query_history_k_data_plus(index_code,
            'date,close',
            start_date=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            frequency='d', adjustflag='2')
        
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        
        if not data:
            return MarketRegime.NEUTRAL
        
        df = pd.DataFrame(data, columns=['date', 'close'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        latest = df.iloc[-1]
        if latest['ma20'] > latest['ma60']:
            return MarketRegime.BULL
        elif latest['ma20'] < latest['ma60']:
            return MarketRegime.BEAR
        else:
            return MarketRegime.NEUTRAL
    
    def analyze_stock(self, code: str, name: str) -> Dict:
        """分析单只股票"""
        # 获取数据
        rs = bs.query_history_k_data_plus(code,
            'date,open,high,low,close,volume,pctChg',
            start_date=(datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            frequency='d', adjustflag='2')
        
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        
        if not data:
            return None
        
        df = pd.DataFrame(data, columns=['date','open','high','low','close','volume','pctChg'])
        for col in ['open','high','low','close','volume','pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 市场状态
        market_state = self.get_market_state()
        
        # 上下文
        context = {
            'weights': self.engine.weights,
            'market_state': market_state,
        }
        
        # 决策
        return self.engine.decide(code, name, df, market_state, context)
    
    def analyze_portfolio(self, stocks: List[Tuple[str, str]]) -> List[Dict]:
        """分析股票组合"""
        self.connect()
        results = []
        for code, name in stocks:
            try:
                result = self.analyze_stock(code, name)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error analyzing {name}: {e}")
        self.disconnect()
        return results

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("虾米量化系统 - 统一Agent工作流")
    print("="*80)
    
    workflow = TradingWorkflow()
    
    # 测试股票池
    test_stocks = [
        ("sz.002371", "北方华创"),
        ("sz.002025", "航天电器"),
        ("sh.600519", "贵州茅台"),
        ("sz.000977", "浪潮信息"),
        ("sz.300750", "宁德时代"),
    ]
    
    results = workflow.analyze_portfolio(test_stocks)
    
    print("\n" + "="*80)
    print("分析结果")
    print("="*80)
    
    for r in results:
        emoji = "🟢" if r['signal'] == 'BUY' else ("🟡" if r['signal'] == 'HOLD' else "🔴")
        print(f"\n{emoji} {r['name']}({r['code']})")
        print(f"   信号: {r['signal']} | 评分: {r['score']} | 置信度: {r['confidence']}")
        print(f"   仓位: {r['position']} | 止损: {r['stop_loss']}")
        print(f"   理由: {', '.join(r['reasons'][:3])}")
        if r['warnings']:
            print(f"   警告: {', '.join(r['warnings'][:2])}")

if __name__ == "__main__":
    main()
