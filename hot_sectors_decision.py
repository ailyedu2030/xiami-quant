#!/usr/bin/env python3
"""
热门板块 + 决策委员会 + 增强技术指标
完整版股票分析决策系统
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import json

# ==================== 热门板块配置 ====================
HOT_SECTORS = {
    "AI人工智能": {
        "codes": ["002230", "002415", "000977", "688041"],
        "names": ["科大讯飞", "海康威视", "浪潮信息", "海光信息"],
        "热度": "🔥🔥🔥🔥🔥",
        "理由": "政策加持+产业趋势+业绩爆发"
    },
    "新能源汽车": {
        "codes": ["300750", "002594", "300014"],
        "names": ["宁德时代", "比亚迪", "亿纬锂能"],
        "热度": "🔥🔥🔥🔥",
        "理由": "渗透率提升+海外扩张+技术领先"
    },
    "半导体": {
        "codes": ["688981", "688012", "603986"],
        "names": ["中芯国际", "中微公司", "兆易创新"],
        "热度": "🔥🔥🔥🔥",
        "理由": "国产替代+周期复苏+政策攻坚"
    },
    "白酒消费": {
        "codes": ["600519", "000858", "000568"],
        "names": ["贵州茅台", "五粮液", "泸州老窖"],
        "热度": "🔥🔥",
        "理由": "防御性强+高ROE+品牌溢价"
    },
    "军工": {
        "codes": ["600760", "002025", "300699"],
        "names": ["中航沈飞", "航天电器", "光威复材"],
        "热度": "🔥🔥🔥",
        "理由": "地缘风险+装备现代化+国企改革"
    }
}

# ==================== 增强技术指标计算 ====================
def calculate_enhanced_indicators(code):
    """计算增强技术指标"""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        symbol, 'date,open,high,low,close,volume,pctChg',
        start_date=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        end_date='2026-04-09', frequency='d', adjustflag='2'
    )
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if len(data) < 30:
        return None
    
    df = pd.DataFrame(data, columns=rs.fields)
    for col in ['open','high','low','close','volume','pctChg']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    results = {}
    
    # === 均线 ===
    ma5 = close.rolling(5).mean().iloc[-1]
    ma10 = close.rolling(10).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    
    results['ma5'] = round(ma5, 2)
    results['ma10'] = round(ma10, 2)
    results['ma20'] = round(ma20, 2)
    results['ma60'] = round(ma60, 2)
    results['ma_bullish'] = ma5 > ma10 > ma20 and close.iloc[-1] > ma5
    results['ma_golden_cross'] = ma5 > ma10
    results['price_vs_ma20'] = close.iloc[-1] > ma20
    
    # === MACD ===
    exp12 = close.ewm(span=12, adjust=False).mean()
    exp26 = close.ewm(span=26, adjust=False).mean()
    macd_line = exp12 - exp26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    
    results['macd'] = round(macd_line.iloc[-1], 4)
    results['macd_signal'] = round(signal_line.iloc[-1], 4)
    results['macd_histogram'] = round(histogram.iloc[-1], 4)
    results['macd_bullish'] = macd_line.iloc[-1] > signal_line.iloc[-1] and histogram.iloc[-1] > 0
    results['macd_histogram_prev'] = histogram.iloc[-5:].mean()
    results['macd_momentum'] = 'accelerating' if histogram.iloc[-1] > histogram.iloc[-5:].mean() else 'weakening'
    
    # === RSI ===
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs_val = gain / loss
    rsi = 100 - (100 / (1 + rs_val))
    results['rsi'] = round(rsi.iloc[-1], 1)
    results['rsi_zone'] = 'overbought' if rsi.iloc[-1] > 70 else ('oversold' if rsi.iloc[-1] < 30 else 'neutral')
    results['rsi_bullish_zone'] = rsi.iloc[-1] > 50
    
    # === KDJ ===
    period = 9
    low_n = low.rolling(period).min()
    high_n = high.rolling(period).max()
    rsv = (close - low_n) / (high_n - low_n) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    results['kdj_k'] = round(k.iloc[-1], 1)
    results['kdj_d'] = round(d.iloc[-1], 1)
    results['kdj_j'] = round(j.iloc[-1], 1)
    results['kdj_bullish'] = k.iloc[-1] > d.iloc[-1] and k.iloc[-1] < 80
    results['kdj_golden_cross'] = k.iloc[-2] < d.iloc[-2] and k.iloc[-1] > d.iloc[-1]
    results['kdj_death_cross'] = k.iloc[-2] > d.iloc[-2] and k.iloc[-1] < d.iloc[-1]
    
    # === 布林带 ===
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    price = close.iloc[-1]
    bb_position = (price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
    results['bb_upper'] = round(bb_upper.iloc[-1], 2)
    results['bb_mid'] = round(bb_mid.iloc[-1], 2)
    results['bb_lower'] = round(bb_lower.iloc[-1], 2)
    results['bb_position'] = round(bb_position * 100, 1)
    results['bb_squeeze'] = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) < close.rolling(20).std().iloc[-1] * 1.5
    results['bb_price_in_band'] = bb_lower.iloc[-1] < price < bb_upper.iloc[-1]
    
    # === ATR ===
    high_low = high - low
    high_close = abs(high - close.shift())
    low_close = abs(low - close.shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    results['atr'] = round(atr.iloc[-1], 2)
    results['atr_percent'] = round(atr.iloc[-1] / close.iloc[-1] * 100, 2)
    results['volatility_high'] = results['atr_percent'] > 5
    
    # === DMI/ADX ===
    high_diff = high.diff()
    low_diff = -low.diff()
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    tr14 = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / tr14)
    minus_di = 100 * (minus_dm.rolling(14).mean() / tr14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(14).mean()
    results['dmi_plus_di'] = round(plus_di.iloc[-1], 1)
    results['dmi_minus_di'] = round(minus_di.iloc[-1], 1)
    results['dmi_adx'] = round(adx.iloc[-1], 1)
    results['dmi_bullish'] = plus_di.iloc[-1] > minus_di.iloc[-1] and adx.iloc[-1] > 20
    results['dmi_strong_trend'] = adx.iloc[-1] > 25
    
    # === CCI ===
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(14).mean()
    mad = tp.rolling(14).apply(lambda x: abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mad)
    results['cci'] = round(cci.iloc[-1], 1)
    results['cci_overbought'] = cci.iloc[-1] > 100
    results['cci_oversold'] = cci.iloc[-1] < -100
    
    # === OBV ===
    obv = (np.sign(close.diff()) * volume).cumsum()
    results['obv'] = round(obv.iloc[-1], 0)
    results['obv_trend'] = 'rising' if obv.iloc[-1] > obv.iloc[-10] else 'falling'
    results['obv_bullish'] = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
    
    # === MFI ===
    tp_mf = (high + low + close) / 3 * volume
    pos_mf = tp_mf.where(close > close.shift(1), 0).rolling(14).sum()
    neg_mf = tp_mf.where(close < close.shift(1), 0).rolling(14).sum()
    mr = pos_mf / neg_mf
    mfi = 100 - (100 / (1 + mr))
    results['mfi'] = round(mfi.iloc[-1], 1)
    results['mfi_overbought'] = mfi.iloc[-1] > 80
    results['mfi_oversold'] = mfi.iloc[-1] < 20
    
    # === SAR ===
    sar = close.copy()
    trend = [1]
    af = 0.02
    ep = 0
    for i in range(1, len(close)):
        if trend[-1] == 1:
            sar.iloc[i] = sar.iloc[i-1] + af * (high.iloc[i-1] - sar.iloc[i-1])
            if low.iloc[i] < sar.iloc[i]:
                trend.append(-1)
                sar.iloc[i] = high.iloc[i-1]
                af = 0.02
            else:
                trend.append(1)
                ep = max(ep, high.iloc[i-1]) if i == 1 else ep
        else:
            sar.iloc[i] = sar.iloc[i-1] + af * (low.iloc[i-1] - sar.iloc[i-1])
            if high.iloc[i] > sar.iloc[i]:
                trend.append(1)
                sar.iloc[i] = low.iloc[i-1]
                af = 0.02
            else:
                trend.append(-1)
                ep = min(ep, low.iloc[i-1]) if i == 1 else ep
    results['sar'] = round(sar.iloc[-1], 2)
    results['sar_trend'] = 'bullish' if trend[-1] == 1 else 'bearish'
    
    # === 量价 ===
    vol_ma5 = volume.rolling(5).mean().iloc[-1]
    results['volume'] = volume.iloc[-1]
    results['vol_ratio'] = round(volume.iloc[-1] / vol_ma5, 2)
    results['volume_surge'] = results['vol_ratio'] > 1.5
    results['volume_shrink'] = results['vol_ratio'] < 0.7
    
    # === 综合评分 ===
    score = 0
    if results['ma_bullish']: score += 20
    if results['macd_bullish']: score += 15
    if results['kdj_bullish'] and not results['kdj_overbought']: score += 10
    if results['rsi_bullish_zone'] and results['rsi_zone'] == 'neutral': score += 10
    if results['dmi_bullish']: score += 10
    if results['volume_surge']: score += 10
    if results['sar_trend'] == 'bullish': score += 10
    if results['obv_bullish']: score += 5
    if results['bb_position'] > 50: score += 5
    if results['macd_momentum'] == 'accelerating': score += 5
    
    results['technical_score'] = min(100, score)
    results['technical_grade'] = 'A' if score >= 80 else ('B' if score >= 60 else ('C' if score >= 40 else 'D'))
    
    return results


# ==================== 决策委员会 ====================
class DecisionCommittee:
    def __init__(self, name, code, data):
        self.name = name
        self.code = code
        self.data = data
        self.votes = {}
    
    def trend_vote(self):
        """趋势委员"""
        score = 50
        reasons = []
        
        if self.data.get('ma_bullish'):
            score += 25
            reasons.append("均线多头排列")
        elif self.data.get('ma_golden_cross'):
            score += 10
            reasons.append("均线金叉")
        
        if self.data.get('macd_bullish'):
            score += 20
            reasons.append("MACD金叉")
        if self.data.get('macd_momentum') == 'accelerating':
            score += 5
            reasons.append("MACD动能增强")
        
        if self.data.get('sar_trend') == 'bullish':
            score += 10
            reasons.append("SAR上升趋势")
        elif self.data.get('sar_trend') == 'bearish':
            score -= 10
            reasons.append("SAR下降趋势")
        
        if self.data.get('dmi_strong_trend'):
            score += 10
            reasons.append("ADX趋势明显")
        
        vote = "BUY" if score >= 70 else ("HOLD" if score >= 50 else "AVOID")
        self.votes['趋势委员'] = {"vote": vote, "score": score, "reasons": reasons}
        return vote, score, reasons
    
    def momentum_vote(self):
        """动能委员"""
        score = 50
        reasons = []
        
        rsi = self.data.get('rsi', 50)
        if 40 <= rsi <= 60:
            score += 15
            reasons.append(f"RSI健康={rsi}")
        elif rsi > 70:
            score -= 15
            reasons.append(f"RSI超买={rsi}")
        elif rsi < 30:
            score += 10
            reasons.append(f"RSI超卖={rsi}")
        
        kdj = self.data.get('kdj', {})
        if self.data.get('kdj_bullish'):
            score += 15
            reasons.append("KDJ多方")
        if self.data.get('kdj_golden_cross'):
            score += 10
            reasons.append("KDJ金叉")
        
        cci = self.data.get('cci', 0)
        if cci > 100:
            score -= 10
            reasons.append(f"CCI超买={cci}")
        elif cci < -100:
            score += 10
            reasons.append(f"CCI超卖={cci}")
        
        if self.data.get('cci_overbought'):
            score -= 10
        if self.data.get('cci_oversold'):
            score += 10
        
        vote = "BUY" if score >= 65 else ("HOLD" if score >= 45 else "AVOID")
        self.votes['动能委员'] = {"vote": vote, "score": score, "reasons": reasons}
        return vote, score, reasons
    
    def money_vote(self):
        """资金委员"""
        score = 50
        reasons = []
        
        vol_ratio = self.data.get('vol_ratio', 1)
        if vol_ratio > 1.5:
            score += 20
            reasons.append(f"成交量放大{vol_ratio}倍")
        elif vol_ratio > 1.2:
            score += 10
            reasons.append("成交量温和放大")
        elif vol_ratio < 0.7:
            score -= 10
            reasons.append("成交量萎缩")
        
        mfi = self.data.get('mfi', 50)
        if 20 <= mfi <= 80:
            score += 10
            reasons.append(f"MFI健康={mfi}")
        elif mfi > 80:
            score -= 15
            reasons.append(f"MFI资金超买={mfi}")
        elif mfi < 20:
            score += 15
            reasons.append(f"MFI资金超卖={mfi}")
        
        if self.data.get('obv_trend') == 'rising':
            score += 10
            reasons.append("OBV上升")
        elif self.data.get('obv_trend') == 'falling':
            score -= 5
            reasons.append("OBV下降")
        
        vote = "BUY" if score >= 65 else ("HOLD" if score >= 45 else "AVOID")
        self.votes['资金委员'] = {"vote": vote, "score": score, "reasons": reasons}
        return vote, score, reasons
    
    def risk_vote(self):
        """风控委员"""
        score = 100
        reasons = []
        price = self.data.get('ma20', self.data.get('ma5', 0))
        
        rsi = self.data.get('rsi', 50)
        if rsi > 80:
            score -= 30
            reasons.append(f"RSI严重超买")
        elif rsi > 70:
            score -= 20
            reasons.append(f"RSI超买风险")
        
        gain_5d = self.data.get('gain_5d', 0)
        if gain_5d > 15:
            score -= 20
            reasons.append(f"5日涨幅{gain_5d:.1f}%过大")
        elif gain_5d > 10:
            score -= 10
            reasons.append(f"5日涨幅{gain_5d:.1f}%注意回吐")
        
        if self.data.get('volatility_high'):
            score -= 10
            reasons.append("波动率偏高")
        
        bb_pos = self.data.get('bb_position', 50)
        if bb_pos > 90:
            score -= 20
            reasons.append("布林带上轨压力")
        elif bb_pos < 10:
            score += 10
            reasons.append("布林带下轨支撑")
        
        if self.data.get('atr_percent', 0) > 5:
            score -= 10
            reasons.append("ATR波动大")
        
        # 止损位
        stop_loss = price * 0.92 if price else 0
        stop_pct = 8
        
        vote = "BUY" if score >= 70 else ("HOLD" if score >= 50 else "AVOID")
        self.votes['风控委员'] = {"vote": vote, "score": score, "reasons": reasons, "stop_loss": f"{stop_loss:.2f}", "stop_pct": f"{stop_pct}%" if stop_loss else "N/A"}
        return vote, score, reasons
    
    def timing_vote(self):
        """时机委员"""
        score = 50
        reasons = []
        
        # 板块轮动 (简化)
        sector_hot = self.data.get('sector_hotness', 3)
        if sector_hot >= 4:
            score += 15
            reasons.append(f"热门板块热度{sector_hot}")
        elif sector_hot <= 2:
            score -= 10
            reasons.append("板块关注度低")
        
        # 布林带
        if self.data.get('bb_squeeze'):
            score += 15
            reasons.append("布林带收口，突破在即")
        
        if self.data.get('bb_position') > 80:
            score -= 10
            reasons.append("接近布林上轨")
        elif self.data.get('bb_position') < 20:
            score += 15
            reasons.append("布林带下轨支撑")
        
        # ADX趋势强度
        adx = self.data.get('dmi_adx', 0)
        if adx > 25:
            score += 10
            reasons.append(f"趋势明显(ADX={adx})")
        
        vote = "BUY" if score >= 60 else ("HOLD" if score >= 45 else "AVOID")
        self.votes['时机委员'] = {"vote": vote, "score": score, "reasons": reasons}
        return vote, score, reasons
    
    def conduct_meeting(self):
        """召开决策会议"""
        print(f"\n{'='*70}")
        print(f"  🏛️ 决策委员会会议 - {self.name}({self.code})")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}")
        
        # 各委员投票
        self.trend_vote()
        self.momentum_vote()
        self.money_vote()
        self.risk_vote()
        self.timing_vote()
        
        # 打印各委员意见
        for member, result in self.votes.items():
            vote_emoji = "🟢" if result['vote'] == 'BUY' else ("🟡" if result['vote'] == 'HOLD' else "🔴")
            print(f"\n📋 {member}")
            print(f"   投票: {vote_emoji} {result['vote']} | 得分: {result['score']}")
            print(f"   理由: {', '.join(result['reasons']) if result['reasons'] else '无明显信号'}")
            if 'stop_loss' in result:
                print(f"   止损: {result['stop_loss']}元 ({result['stop_pct']})")
        
        # 统计投票
        votes = [v['vote'] for v in self.votes.values()]
        buy = votes.count("BUY")
        hold = votes.count("HOLD")
        avoid = votes.count("AVOID")
        
        print(f"\n{'='*70}")
        print(f"📊 投票汇总: 🟢买入={buy} | 🟡持有={hold} | 🔴回避={avoid}")
        
        # 决策
        if buy >= 3:
            decision = "🟢 BUY (建议买入)"
            final_decision = "BUY"
        elif buy + hold >= 3:
            decision = "🟡 HOLD (建议持有)"
            final_decision = "HOLD"
        else:
            decision = "🔴 AVOID (建议回避)"
            final_decision = "AVOID"
        
        # 综合评分
        avg_score = sum(v['score'] for v in self.votes.values()) / len(self.votes)
        
        print(f"🏛️ 委员会决策: {decision}")
        print(f"📈 综合评分: {avg_score:.0f}/100")
        
        # 风控建议
        risk_result = self.votes.get('风控委员', {})
        if 'stop_loss' in risk_result:
            print(f"🛡️ 止损建议: {risk_result.get('stop_loss', 'N/A')}元 ({risk_result.get('stop_pct', 'N/A')})")
        
        # 买入信号汇总
        buy_signals = []
        sell_signals = []
        
        if self.data.get('ma_bullish'): buy_signals.append("均线多头")
        if self.data.get('macd_bullish'): buy_signals.append("MACD金叉")
        if self.data.get('kdj_golden_cross'): buy_signals.append("KDJ金叉")
        if self.data.get('volume_surge'): buy_signals.append("成交量放大")
        if self.data.get('bb_squeeze'): buy_signals.append("布林带收敛")
        if self.data.get('rsi_zone') == 'oversold': buy_signals.append("RSI超卖")
        if self.data.get('mfi_oversold'): buy_signals.append("MFI超卖")
        if self.data.get('sar_trend') == 'bullish': buy_signals.append("SAR看涨")
        
        if self.data.get('rsi_zone') == 'overbought': sell_signals.append("RSI超买")
        if self.data.get('mfi_overbought'): sell_signals.append("MFI超买")
        if self.data.get('kdj_death_cross'): sell_signals.append("KDJ死叉")
        
        print(f"\n✅ 买入信号({len(buy_signals)}): {', '.join(buy_signals) if buy_signals else '无'}")
        print(f"❌ 卖出信号({len(sell_signals)}): {', '.join(sell_signals) if sell_signals else '无'}")
        print(f"🎯 技术评级: {self.data.get('technical_score', 0)}/100 ({self.data.get('technical_grade', 'N')})")
        print(f"{'='*70}")
        
        return {
            "decision": final_decision,
            "votes": {"buy": buy, "hold": hold, "avoid": avoid},
            "avg_score": round(avg_score, 1),
            "stop_loss": risk_result.get('stop_loss', 'N/A'),
            "stop_pct": risk_result.get('stop_pct', 'N/A'),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "technical_score": self.data.get('technical_score', 0),
            "technical_grade": self.data.get('technical_grade', 'N')
        }


# ==================== 主程序 ====================
def analyze_hot_sectors():
    """分析热门板块"""
    print(f"\n{'='*70}")
    print(f"  🔥 虾米热门板块 + 决策委员会系统")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    
    all_results = {}
    
    for sector_name, sector_info in HOT_SECTORS.items():
        print(f"\n📊 {sector_name} {sector_info['热度']}")
        print(f"   理由: {sector_info['理由']}")
        print("-" * 60)
        
        sector_stocks = []
        
        for code, name in zip(sector_info["codes"], sector_info["names"]):
            try:
                data = calculate_enhanced_indicators(code)
                if data:
                    data['sector'] = sector_name
                    data['sector_hotness'] = 4 if sector_info["热度"].count("🔥") >= 4 else 3
                    data['gain_5d'] = round((data.get('ma5', 0) / data.get('ma5', 1) - 1) * 100, 2) if data.get('ma5') else 0
                    
                    status = "🟢" if data['technical_score'] >= 60 else ("🟡" if data['technical_score'] >= 40 else "🔴")
                    print(f"   {status} {name}({code}) {data['price']}元 | RSI={data['rsi']} | MACD={'金叉' if data['macd_bullish'] else '死叉'} | KDJ={'多头' if data['kdj_bullish'] else '空头'} | 评分:{data['technical_score']}")
                    
                    sector_stocks.append((name, code, data))
            except Exception as e:
                print(f"   ❌ {name}({code}) 数据失败")
        
        if sector_stocks:
            # 找出板块最强
            best = max(sector_stocks, key=lambda x: x[2].get('technical_score', 0))
            all_results[sector_name] = {
                "热度": sector_info['热度'],
                "理由": sector_info['理由'],
                "最强股": best[0],
                "最强股代码": best[1],
                "最强股评分": best[2].get('technical_score', 0),
                "最强股指标": best[2]
            }
    
    return all_results


def run_committee_on_stock(name, code, data):
    """对单只股票开决策委员会"""
    committee = DecisionCommittee(name, code, data)
    return committee.conduct_meeting()


def print_final_recommendation(all_results):
    """打印最终推荐"""
    print(f"\n{'='*70}")
    print(f"  🏆 今日最终推荐")
    print(f"{'='*70}")
    
    # 按评分排序
    sorted_stocks = []
    for sector, data in all_results.items():
        sorted_stocks.append({
            "sector": sector,
            "name": data['最强股'],
            "code": data['最强股代码'],
            "score": data['最强股评分'],
            "indicators": data['最强股指标']
        })
    
    sorted_stocks.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n🏅 TOP 3 推荐:")
    for i, stock in enumerate(sorted_stocks[:3], 1):
        print(f"\n  {i}. {stock['name']}({stock['code']}) - {stock['sector']}")
        print(f"     技术评分: {stock['score']}/100")
        ind = stock['indicators']
        print(f"     RSI={ind.get('rsi','N/A')} | MACD={'金叉' if ind.get('macd_bullish') else '整理'} | KDJ={'多头' if ind.get('kdj_bullish') else '空头'}")
        print(f"     布林带位置: {ind.get('bb_position','N/A')}%")
        print(f"     MFI={ind.get('mfi','N/A')} | 成交量比={ind.get('vol_ratio','N/A')}")
    
    # 对TOP1开决策委员会
    if sorted_stocks:
        top = sorted_stocks[0]
        print(f"\n{'='*70}")
        print(f"  🎯 对最强标的进行决策委员会审议")
        print(f"{'='*70}")
        run_committee_on_stock(top['name'], top['code'], top['indicators'])
    
    print(f"\n⚠️ 免责声明: 本分析仅供参考，不构成投资建议")
    print(f"{'='*70}")


if __name__ == "__main__":
    results = analyze_hot_sectors()
    print_final_recommendation(results)
