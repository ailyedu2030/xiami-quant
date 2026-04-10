#!/usr/bin/env python3
"""
虾米量化系统 - 完整集成版 v2.0
Integrated Trading System

整合所有Agent和工作流:
1. TechnicalAgent - 技术面分析
2. Tactic2560Agent - 2560战法
3. RiskAgent - 风险分析
4. PositionAgent - 仓位管理
5. SectorRotationAgent - 板块轮动
6. PositionTracker - 持仓跟踪

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import baostock as bs
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# ==================== 配置 ====================

STOCK_POOL = [
    # 核心持仓
    ("sz.002371", "北方华创", "半导体"),
    ("sh.600519", "贵州茅台", "白酒"),
    ("sh.600276", "恒瑞医药", "医药"),
    ("sz.000977", "浪潮信息", "AI"),
    ("sz.002025", "航天电器", "军工"),
    # 备选池
    ("sz.300750", "宁德时代", "新能源"),
    ("sh.688012", "中微公司", "半导体"),
    ("sh.600309", "万华化学", "化工"),
    ("sz.002594", "比亚迪", "新能源"),
    ("sh.600887", "伊利股份", "乳业"),
]

SECTOR_MAP = {
    '半导体': ['sz.002371', 'sh.688012'],
    '医药': ['sh.600276', 'sh.603259'],
    '新能源': ['sz.300750', 'sz.002594', 'sz.002812'],
    '军工': ['sz.002025'],
    '白酒': ['sh.600519'],
    'AI': ['sz.000977'],
}

# ==================== 数据类 ====================

@dataclass
class SignalResult:
    """统一信号格式"""
    agent: str
    signal: str  # BUY/HOLD/AVOID
    score: float
    confidence: str  # HIGH/MED/LOW
    reasons: List[str]
    warnings: List[str]
    data: Dict

# ==================== Agent实现 ====================

class TechnicalAgent:
    """技术面Agent"""
    
    def analyze(self, df: pd.DataFrame, market_state: str) -> SignalResult:
        close = df['close']
        volume = df['volume']
        
        score = 50
        reasons = []
        warnings = []
        data = {}
        
        # 均线
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        
        if ma5 > ma20 > ma60:
            score += 20
            reasons.append("均线多头")
        elif ma5 < ma20 < ma60:
            score -= 15
            warnings.append("均线空头")
        
        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal.iloc[-1]:
            score += 15
            reasons.append("MACD金叉")
        else:
            score -= 10
            warnings.append("MACD死叉")
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_val = gain / loss
        rsi = (100 - (100 / (1 + rs_val))).iloc[-1]
        data['rsi'] = float(rsi)
        
        if 40 <= rsi <= 60:
            score += 10
            reasons.append(f"RSI健康({rsi:.0f})")
        elif rsi > 70:
            warnings.append(f"RSI超买({rsi:.0f})")
        elif rsi < 30:
            reasons.append(f"RSI超卖({rsi:.0f})")
        
        # 成交量
        vol_ma = volume.rolling(20).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma if vol_ma > 0 else 1
        data['vol_ratio'] = float(vol_ratio)
        
        if vol_ratio > 1.5:
            score += 10
            reasons.append(f"放量({vol_ratio:.1f}x)")
        elif vol_ratio < 0.7:
            warnings.append("缩量")
        
        # 市场状态调整
        if market_state == 'BEAR' and score > 60:
            score = 60
        
        signal = 'BUY' if score >= 65 else ('AVOID' if score < 40 else 'HOLD')
        confidence = 'HIGH' if abs(score - 50) > 20 else 'MED'
        
        return SignalResult(
            agent='TechnicalAgent',
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
            data=data
        )

class Tactic2560Agent:
    """2560战术Agent"""
    
    def analyze(self, df: pd.DataFrame, market_state: str, weights: Dict) -> SignalResult:
        close = df['close']
        volume = df['volume']
        
        score = 50
        reasons = []
        warnings = []
        data = {}
        
        # MA25趋势
        ma25 = close.rolling(25).mean()
        ma25_trend = ma25.iloc[-1] - ma25.iloc[-5]
        ma25_up = ma25_trend > 0
        data['ma25_up'] = ma25_up
        
        # 量能金叉死叉
        vol_ma5 = volume.rolling(5).mean()
        vol_ma60 = volume.rolling(60).mean()
        
        vol_now = vol_ma5.iloc[-1]
        vol_prev = vol_ma5.iloc[-2]
        vol_60_now = vol_ma60.iloc[-1]
        vol_60_prev = vol_ma60.iloc[-2]
        
        vol_golden = (vol_now > vol_60_now) and (vol_prev <= vol_60_prev)
        vol_dead = (vol_now < vol_60_now) and (vol_prev >= vol_60_prev)
        data['vol_golden'] = vol_golden
        data['vol_dead'] = vol_dead
        
        # 信号判断
        if ma25_up and vol_golden:
            score += 40
            reasons.append("MA25向上+量能金叉")
        elif vol_golden:
            score += 20
            reasons.append("量能金叉")
        elif ma25_up:
            score += 10
            reasons.append("MA25向上")
        
        if vol_dead:
            score -= 20
            warnings.append("量能死叉")
        
        # 优化权重影响
        if weights.get('vol_breakout', 0) > 0.5 and vol_golden:
            score += 10
        
        signal = 'BUY' if score >= 65 else ('AVOID' if score < 45 else 'HOLD')
        confidence = 'HIGH' if abs(score - 50) > 25 else 'MED'
        
        return SignalResult(
            agent='Tactic2560Agent',
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
            data=data
        )

class RiskAgent:
    """风险Agent"""
    
    def __init__(self):
        self._load_risk_data()
    
    def _load_risk_data(self):
        try:
            with open('comprehensive_results.json', 'r') as f:
                data = json.load(f)
                self.var_data = data.get('var', {})
                self.dd_data = data.get('drawdown', {})
                self.beta_data = data.get('beta', {})
        except:
            self.var_data = {}
            self.dd_data = {}
            self.beta_data = {}
    
    def analyze(self, name: str, market_state: str) -> SignalResult:
        score = 50
        reasons = []
        warnings = []
        data = {}
        
        # VaR
        var_info = self.var_data.get(name, {})
        if var_info:
            var_95 = var_info.get('var95', 0)
            data['var_95'] = var_95
            if abs(var_95) < 2:
                score += 15
                reasons.append(f"VaR低({var_95}%)")
            elif abs(var_95) > 4:
                score -= 20
                warnings.append(f"VaR高({var_95}%)")
        
        # 回撤
        dd_info = self.dd_data.get(name, {})
        if dd_info:
            max_dd = dd_info.get('max_drawdown_pct', 0)
            data['max_drawdown'] = max_dd
            if abs(max_dd) < 15:
                score += 10
                reasons.append(f"回撤小({max_dd:.1f}%)")
            elif abs(max_dd) > 25:
                score -= 20
                warnings.append(f"回撤大({max_dd:.1f}%)")
        
        # Beta
        beta_info = self.beta_data.get(name, {})
        if beta_info:
            beta = beta_info.get('beta', 1.0)
            data['beta'] = beta
            if beta < 0.8:
                score += 10
                reasons.append(f"低Beta({beta})")
            elif beta > 1.5:
                score -= 10
                warnings.append(f"高Beta({beta})")
        
        # 熊市调整
        if market_state == 'BEAR' and score > 50:
            score = 50 + (score - 50) * 0.5
        
        signal = 'BUY' if score >= 65 else ('AVOID' if score < 40 else 'HOLD')
        confidence = 'HIGH' if abs(score - 50) > 20 else 'MED'
        
        return SignalResult(
            agent='RiskAgent',
            signal=signal,
            score=min(100, max(0, score)),
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
            data=data
        )

class PositionAgent:
    """仓位Agent"""
    
    def analyze(self, df: pd.DataFrame, market_state: str, 
                win_rate: float = 0.6, avg_win: float = 2.0, avg_loss: float = 1.5) -> SignalResult:
        close = df['close']
        high = df['high']
        low = df['low']
        
        score = 50
        reasons = []
        warnings = []
        data = {}
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = atr / close.iloc[-1] * 100
        data['atr'] = float(atr)
        data['atr_pct'] = float(atr_pct)
        
        # 止损位
        stop_loss = close.iloc[-1] - 2 * atr
        data['stop_loss'] = float(stop_loss)
        
        # 凯利
        if avg_loss > 0:
            b = avg_win / avg_loss
            kelly = (win_rate * b - (1 - win_rate)) / b
            safe_kelly = kelly * 0.5
            max_pos = min(safe_kelly, 0.25)
        else:
            kelly = 0
            max_pos = 0.1
        
        data['kelly'] = float(kelly)
        data['max_position'] = float(max_pos)
        data['recommended_position'] = f"{int(min(25, max_pos * 100))}%"
        
        # 评分
        if max_pos >= 0.2:
            score += 15
            reasons.append(f"建议仓位{int(max_pos*100)}%")
        elif max_pos >= 0.1:
            score += 5
        else:
            score -= 10
            warnings.append("建议轻仓")
        
        # 熊市降低
        if market_state == 'BEAR':
            max_pos *= 0.7
            data['adjusted_position'] = f"{int(max_pos * 100)}%"
            warnings.append("熊市降仓")
        
        signal = 'BUY' if score >= 60 else ('AVOID' if score < 40 else 'HOLD')
        
        return SignalResult(
            agent='PositionAgent',
            signal=signal,
            score=min(100, max(0, score)),
            confidence='MED',
            reasons=reasons,
            warnings=warnings,
            data=data
        )

class SectorRotationAgent:
    """板块轮动Agent"""
    
    def analyze(self, sector: str) -> Tuple[str, float]:
        """返回 (板块状态, 动量分数)"""
        momentum_data = {
            '半导体': 3.7,
            '医药': 2.5,
            '新能源': 0.7,
            '军工': 9.7,
            '白酒': 4.5,
            'AI': 1.0,
        }
        
        momentum = momentum_data.get(sector, 0)
        
        if momentum > 5:
            return 'LEADING', momentum
        elif momentum > 2:
            return 'MOMENTUM', momentum
        elif momentum > 0:
            return 'STABLE', momentum
        else:
            return 'WEAK', momentum

# ==================== 持仓跟踪 ====================

class PositionTracker:
    """持仓跟踪器"""
    
    def __init__(self, file_path: str = 'positions.json'):
        self.file_path = file_path
        self.positions = {}
        self.load()
    
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.positions = json.load(f)
    
    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.positions, f, indent=2, ensure_ascii=False)
    
    def add(self, code: str, name: str, buy_price: float, quantity: int, buy_date: str):
        self.positions[code] = {
            'name': name,
            'buy_price': buy_price,
            'quantity': quantity,
            'buy_date': buy_date,
            'stop_loss': round(buy_price * 0.92, 2),
            'target': round(buy_price * 1.15, 2),
        }
        self.save()
    
    def check(self, code: str, current_price: float) -> Optional[Dict]:
        if code not in self.positions:
            return None
        
        pos = self.positions[code]
        buy = pos['buy_price']
        pnl = (current_price - buy) / buy * 100
        stop = pos['stop_loss']
        target = pos['target']
        
        if current_price <= stop:
            signal = "🚨 止损"
            action = "SELL"
        elif current_price >= target:
            signal = "🎯 目标"
            action = "CONSIDER_SELL"
        elif pnl < -3:
            signal = f"⚠️ 亏损{pnl:.1f}%"
            action = "WATCH"
        else:
            signal = f"✅ 盈利{pnl:.1f}%"
            action = "HOLD"
        
        return {
            'signal': signal,
            'action': action,
            'pnl': round(pnl, 2),
            'stop_loss': stop,
            'target': target,
            'current': current_price,
            'buy_price': buy,
        }
    
    def get_all(self) -> Dict:
        return self.positions

# ==================== 决策引擎 ====================

class DecisionEngine:
    """决策引擎"""
    
    def __init__(self):
        self.tech_agent = TechnicalAgent()
        self.tactic_agent = Tactic2560Agent()
        self.risk_agent = RiskAgent()
        self.position_agent = PositionAgent()
        self.sector_agent = SectorRotationAgent()
        self.tracker = PositionTracker()
        
        self._load_weights()
    
    def _load_weights(self):
        try:
            with open('optimal_weights_v2.json', 'r') as f:
                data = json.load(f)
                best = data.get('best_weights', {})
                self.weights = {
                    'vol_breakout': best.get('vol', 0.7),
                    'ma_golden': best.get('ma', 0.2),
                    'rise_3pct': best.get('rise', 0.06),
                    'shrink': best.get('shrink', 0.04),
                }
        except:
            self.weights = {'vol_breakout': 0.7, 'ma_golden': 0.2, 'rise_3pct': 0.06, 'shrink': 0.04}
    
    def get_market_state(self) -> str:
        """判断市场状态"""
        rs = bs.query_history_k_data_plus('sh.000001', 'date,close',
            start_date=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'), frequency='d', adjustflag='2')
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        if not data:
            return 'NEUTRAL'
        
        df = pd.DataFrame(data, columns=['date', 'close'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        latest = df.iloc[-1]
        if latest['ma20'] > latest['ma60']:
            return 'BULL'
        elif latest['ma20'] < latest['ma60']:
            return 'BEAR'
        return 'NEUTRAL'
    
    def get_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        rs = bs.query_history_k_data_plus(code, 'date,open,high,low,close,volume,pctChg',
            start_date=(datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'), frequency='d', adjustflag='2')
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        if not data:
            return None
        
        df = pd.DataFrame(data, columns=['date','open','high','low','close','volume','pctChg'])
        for col in ['open','high','low','close','volume','pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    
    def analyze(self, code: str, name: str, sector: str) -> Dict:
        """完整分析"""
        df = self.get_stock_data(code)
        if df is None:
            return None
        
        market_state = self.get_market_state()
        
        # 各Agent分析
        tech = self.tech_agent.analyze(df, market_state)
        tactic = self.tactic_agent.analyze(df, market_state, self.weights)
        risk = self.risk_agent.analyze(name, market_state)
        position = self.position_agent.analyze(df, market_state)
        sector_state, sector_momentum = self.sector_agent.analyze(sector)
        
        # 加权评分
        weighted_score = (
            tech.score * 0.30 +
            tactic.score * 0.30 +
            risk.score * 0.25 +
            position.score * 0.15
        )
        
        # 综合信号
        buy_count = sum(1 for s in [tech, tactic, risk, position] if s.signal == 'BUY')
        avoid_count = sum(1 for s in [tech, tactic, risk, position] if s.signal == 'AVOID')
        
        if buy_count >= 3:
            final_signal = 'BUY'
        elif avoid_count >= 2:
            final_signal = 'AVOID'
        else:
            final_signal = 'HOLD'
        
        # 收集理由和警告
        all_reasons = []
        all_warnings = []
        for s in [tech, tactic, risk, position]:
            all_reasons.extend(s.reasons)
            all_warnings.extend(s.warnings)
        
        # 持仓检查
        current_price = df['close'].iloc[-1]
        position_status = self.tracker.check(code, current_price)
        
        return {
            'code': code,
            'name': name,
            'sector': sector,
            'market_state': market_state,
            'sector_status': sector_state,
            'sector_momentum': sector_momentum,
            
            'signal': final_signal,
            'score': round(weighted_score, 1),
            
            'technical': {'score': tech.score, 'signal': tech.signal, 'reasons': tech.reasons},
            'tactic': {'score': tactic.score, 'signal': tactic.signal, 'reasons': tactic.reasons},
            'risk': {'score': risk.score, 'signal': risk.signal, 'reasons': risk.reasons},
            'position': {'score': position.score, 'signal': position.signal, 
                        'recommended': position.data.get('recommended_position', '10%'),
                        'stop_loss': position.data.get('stop_loss', 0)},
            
            'reasons': list(set(all_reasons))[:3],
            'warnings': list(set(all_warnings))[:2],
            
            'position_status': position_status,
            'current_price': current_price,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
    
    def analyze_all(self) -> List[Dict]:
        """分析整个股票池"""
        bs.login()
        results = []
        
        print(f"\n市场状态: {self.get_market_state()}")
        print(f"优化权重: vol={self.weights['vol_breakout']:.1%}, ma={self.weights['ma_golden']:.1%}")
        print("-" * 60)
        
        for code, name, sector in STOCK_POOL:
            try:
                result = self.analyze(code, name, sector)
                if result:
                    results.append(result)
                    # 打印摘要
                    emoji = "🟢" if result['signal'] == 'BUY' else ("🟡" if result['signal'] == 'HOLD' else "🔴")
                    pos_info = ""
                    if result['position_status']:
                        pos_info = f" | {result['position_status']['signal']}"
                    print(f"{emoji} {name:<8} {result['signal']:<6} 评分:{result['score']:>5.1f}{pos_info}")
            except Exception as e:
                print(f"❌ {name}: {e}")
        
        bs.logout()
        return results

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("虾米量化系统 - 完整集成版 v2.0")
    print("="*80)
    
    engine = DecisionEngine()
    results = engine.analyze_all()
    
    # 排序输出
    print("\n" + "="*80)
    print("📊 完整分析结果")
    print("="*80)
    
    for r in sorted(results, key=lambda x: -x['score']):
        print(f"\n{r['name']}({r['code']}) - {r['sector']}")
        print(f"  信号: {r['signal']} | 评分: {r['score']}")
        print(f"  技术:{r['technical']['score']:.0f} 战术:{r['tactic']['score']:.0f} 风险:{r['risk']['score']:.0f} 仓位:{r['position']['score']:.0f}")
        print(f"  板块: {r['sector_status']}({r['sector_momentum']:+.1f}%)")
        print(f"  理由: {', '.join(r['reasons'])}")
        if r['warnings']:
            print(f"  警告: {', '.join(r['warnings'])}")
        if r['position_status']:
            ps = r['position_status']
            print(f"  持仓: 买入{ps['buy_price']} 当前{ps['current']} PnL:{ps['pnl']:+.1f}%")
            print(f"       止损:{ps['stop_loss']} 目标:{ps['target']}")

if __name__ == "__main__":
    main()

# ==================== 新闻Agent (追加到文件末尾) ====================

class NewsAgent:
    """新闻事件Agent"""
    
    def __init__(self):
        self.session_start = datetime.now()
    
    def get_market_news(self, hours: int = 24) -> List[Dict]:
        news_list = []
        try:
            df = ak.stock_news_em(symbol="A股")
            for _, row in df.iterrows():
                news_list.append({
                    'title': str(row.get('新闻标题', '')),
                    'content': str(row.get('新闻内容', ''))[:200],
                    'time': str(row.get('发布时间', '')),
                    'source': '东方财富',
                })
        except Exception as e:
            print(f"获取新闻失败: {e}")
        return news_list
    
    def analyze_sentiment(self, news_list: List[Dict]) -> Dict:
        if not news_list:
            return {'sentiment': 'neutral', 'score': 50, 'hot_topics': []}
        
        positive_keywords = ['利好', '涨', '突破', '增长', '盈利', '创新高', '增持', '买入', '推荐', '超预期']
        negative_keywords = ['利空', '跌', '减持', '亏损', '风险', '处罚', '调查', '业绩下滑']
        hot_keywords = ['降准', '降息', 'AI', '人工智能', '新能源', '半导体', '医药', '茅台', '宁德']
        
        scores = []
        hot_topics = []
        
        for news in news_list:
            text = news.get('title', '') + news.get('content', '')
            pos = sum(1 for k in positive_keywords if k in text)
            neg = sum(1 for k in negative_keywords if k in text)
            
            if pos > neg:
                scores.append(70)
            elif neg > pos:
                scores.append(30)
            else:
                scores.append(50)
            
            for k in hot_keywords:
                if k in text and k not in hot_topics:
                    hot_topics.append(k)
        
        avg_score = sum(scores) / len(scores) if scores else 50
        
        return {
            'sentiment': 'positive' if avg_score >= 60 else ('negative' if avg_score <= 40 else 'neutral'),
            'score': round(avg_score, 1),
            'hot_topics': hot_topics[:5]
        }
    
    def analyze_for_stock(self, stock_name: str) -> Dict:
        news = self.get_market_news()
        sentiment = self.analyze_sentiment(news)
        return {'stock': stock_name, 'sentiment': sentiment}
