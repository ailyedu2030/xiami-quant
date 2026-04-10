#!/usr/bin/env python3
"""
专业级技术指标库
包含20+技术指标，为决策委员会提供更全面的技术分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TechnicalIndicators:
    """专业技术指标计算器"""
    
    def __init__(self, df):
        """
        df 需要包含列: open, high, low, close, volume
        """
        self.df = df.copy()
        self.close = pd.to_numeric(df['close'], errors='coerce')
        self.high = pd.to_numeric(df['high'], errors='coerce')
        self.low = pd.to_numeric(df['low'], errors='coerce')
        self.volume = pd.to_numeric(df['volume'], errors='coerce')
        self.results = {}
    
    def calculate_all(self):
        """计算所有指标"""
        self.ma_system()       # 均线系统
        self.macd_system()     # MACD
        self.rsi_system()      # RSI
        self.kdj_system()       # KDJ
        self.bollinger_system() # 布林带
        self.bollinger_system()    # 布林带
        self.obv_system()      # OBV能量潮
        self.atr_system()       # ATR平均真实波幅
        self.dmi_system()      # DMI趋向指标
        self.cci_system()      # CCI顺势指标
        self.williams_system() # 威廉指标
        self.mfi_system()      # MFI资金流量
        self.sar_system()      # SAR抛物线
        self.vwap_system()     # VWAP成交量加权
        self.volume_profile()  # 量价分析
        self.trend_strength()  # 趋势强度
        return self.results
    
    # ==================== 均线系统 ====================
    def ma_system(self):
        """均线系统 - MA5/10/20/60/120/250"""
        ma_periods = [5, 10, 20, 30, 60, 120]
        for p in ma_periods:
            if len(self.close) >= p:
                self.results[f'ma{p}'] = round(self.close.rolling(p).mean().iloc[-1], 2)
        
        # 均线多头/空头排列
        ma5 = self.results.get('ma5', 0)
        ma10 = self.results.get('ma10', 0)
        ma20 = self.results.get('ma20', 0)
        
        self.results['ma_bullish'] = ma5 > ma10 > ma20 and self.close.iloc[-1] > ma5
        self.results['ma_bearish'] = ma5 < ma10 < ma20 and self.close.iloc[-1] < ma5
        self.results['ma_golden_cross'] = self.ma_cross('ma5', 'ma10') == 'golden'
        self.results['ma_death_cross'] = self.ma_cross('ma5', 'ma10') == 'death'
        
        # 价格与均线关系
        self.results['price_vs_ma5'] = 'above' if self.close.iloc[-1] > self.results.get('ma5', 0) else 'below'
        self.results['price_vs_ma20'] = 'above' if self.close.iloc[-1] > self.results.get('ma20', 0) else 'below'
        self.results['price_vs_ma60'] = 'above' if self.close.iloc[-1] > self.results.get('ma60', 0) else 'below'
    
    def ma_cross(self, ma1, ma2):
        """检测均线交叉"""
        if len(self.close) < 20:
            return 'none'
        ma1_vals = self.close.rolling(int(ma1[2:])).mean()
        ma2_vals = self.close.rolling(int(ma2[2:])).mean()
        
        diff_now = ma1_vals.iloc[-1] - ma2_vals.iloc[-1]
        diff_prev = ma1_vals.iloc[-2] - ma2_vals.iloc[-2]
        
        if diff_prev < 0 and diff_now > 0:
            return 'golden'
        elif diff_prev > 0 and diff_now < 0:
            return 'death'
        return 'none'
    
    # ==================== MACD系统 ====================
    def macd_system(self):
        """MACD - 12/26/9"""
        exp12 = self.close.ewm(span=12, adjust=False).mean()
        exp26 = self.close.ewm(span=26, adjust=False).mean()
        macd_line = exp12 - exp26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        self.results['macd'] = round(macd_line.iloc[-1], 4)
        self.results['macd_signal'] = round(signal_line.iloc[-1], 4)
        self.results['macd_histogram'] = round(histogram.iloc[-1], 4)
        
        # MACD信号
        self.results['macd_bullish'] = macd_line.iloc[-1] > signal_line.iloc[-1] and histogram.iloc[-1] > 0
        self.results['macd_bearish'] = macd_line.iloc[-1] < signal_line.iloc[-1] and histogram.iloc[-1] < 0
        
        # MACD背离检测
        self.results['macd_divergence'] = self._detect_divergence(macd_line, 'macd')
        
        # MACD动能
        hist_prev = histogram.iloc[-5:].mean()
        hist_now = histogram.iloc[-1]
        self.results['macd_momentum'] = 'accelerating' if hist_now > hist_prev else 'weakening'
    
    # ==================== RSI系统 ====================
    def rsi_system(self, period=14):
        """RSI相对强弱指标"""
        delta = self.close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        self.results['rsi'] = round(rsi.iloc[-1], 1)
        self.results['rsi_k'] = round(r(50, rsi.iloc[-5:].min(), rsi.iloc[-5:].max()), 1) if rsi.iloc[-5:].max() != rsi.iloc[-5:].min() else 50
        
        # RSI信号
        rsi_val = rsi.iloc[-1]
        self.results['rsi_overbought'] = rsi_val > 80
        self.results['rsi_oversold'] = rsi_val < 20
        self.results['rsi_neutral'] = 40 <= rsi_val <= 60
        self.results['rsi_bullish_zone'] = rsi_val > 50
        self.results['rsi_zone'] = 'overbought' if rsi_val > 70 else ('oversold' if rsi_val < 30 else 'neutral')
    
    # ==================== KDJ系统 ====================
    def kdj_system(self, period=9):
        """KDJ随机指标"""
        low_n = self.low.rolling(period).min()
        high_n = self.high.rolling(period).max()
        
        rsv = (self.close - low_n) / (high_n - low_n) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        self.results['kdj_k'] = round(k.iloc[-1], 1)
        self.results['kdj_d'] = round(d.iloc[-1], 1)
        self.results['kdj_j'] = round(j.iloc[-1], 1)
        
        # KDJ信号
        self.results['kdj_bullish'] = k.iloc[-1] > d.iloc[-1] and k.iloc[-1] < 80
        self.results['kdj_overbought'] = j.iloc[-1] > 90
        self.results['kdj_oversold'] = j.iloc[-1] < 10
        self.results['kdj_golden_cross'] = k.iloc[-2] < d.iloc[-2] and k.iloc[-1] > d.iloc[-1]
        self.results['kdj_death_cross'] = k.iloc[-2] > d.iloc[-2] and k.iloc[-1] < d.iloc[-1]
    
    # ==================== 布林带系统 ====================
    def bollinger_system(self, period=20, std_dev=2):
        """布林带"""
        mid = self.close.rolling(period).mean()
        std = self.close.rolling(period).std()
        upper = mid + std_dev * std
        lower = mid - std_dev * std
        
        self.results['bb_upper'] = round(upper.iloc[-1], 2)
        self.results['bb_mid'] = round(mid.iloc[-1], 2)
        self.results['bb_lower'] = round(lower.iloc[-1], 2)
        
        # 布林带位置
        price = self.close.iloc[-1]
        bb_range = upper.iloc[-1] - lower.iloc[-1]
        bb_position = (price - lower.iloc[-1]) / bb_range if bb_range > 0 else 0.5
        self.results['bb_position'] = round(bb_position * 100, 1)  # 0-100%
        
        # 布林带信号
        self.results['bb_upper_touch'] = price >= upper.iloc[-1] * 0.98
        self.results['bb_lower_touch'] = price <= lower.iloc[-1] * 1.02
        self.results['bb_squeeze'] = bb_range < self.close.rolling(20).std().iloc[-1] * 1.5  # 收口
        self.results['bb_expansion'] = bb_range > self.close.rolling(20).std().iloc[-1] * 2.5  # 开口
        self.results['bb_price_in_band'] = lower.iloc[-1] < price < upper.iloc[-1]
    
    # ==================== ATR系统 ====================
    def atr_system(self, period=14):
        """ATR平均真实波幅"""
        high_low = self.high - self.low
        high_close = np.abs(self.high - self.close.shift())
        low_close = np.abs(self.low - self.close.shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        self.results['atr'] = round(atr.iloc[-1], 2)
        self.results['atr_percent'] = round(atr.iloc[-1] / self.close.iloc[-1] * 100, 2)  # ATR占价格百分比
        
        # 波动率评估
        self.results['volatility_high'] = self.results['atr_percent'] > 5
        self.results['volatility_low'] = self.results['atr_percent'] < 2
        self.results['volatility_normal'] = 2 <= self.results['atr_percent'] <= 5
    
    # ==================== DMI系统 ====================
    def dmi_system(self, period=14):
        """DMI趋向指标"""
        # +DM, -DM
        high_diff = self.high.diff()
        low_diff = -self.low.diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # True Range
        tr1 = self.high - self.low
        tr2 = np.abs(self.high - self.close.shift())
        tr3 = np.abs(self.low - self.close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 平滑
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        self.results['dmi_plus_di'] = round(plus_di.iloc[-1], 1)
        self.results['dmi_minus_di'] = round(minus_di.iloc[-1], 1)
        self.results['dmi_adx'] = round(adx.iloc[-1], 1)
        
        # DMI信号
        self.results['dmi_bullish'] = plus_di.iloc[-1] > minus_di.iloc[-1] and adx.iloc[-1] > 20
        self.results['dmi_strong_trend'] = adx.iloc[-1] > 25
        self.results['dmi_adx_rising'] = adx.iloc[-1] > adx.iloc[-5] if len(adx) >= 5 else False
    
    # ==================== CCI系统 ====================
    def cci_system(self, period=14):
        """CCI顺势指标"""
        tp = (self.high + self.low + self.close) / 3
        sma_tp = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (tp - sma_tp) / (0.015 * mad)
        
        self.results['cci'] = round(cci.iloc[-1], 1)
        
        # CCI信号
        self.results['cci_overbought'] = cci.iloc[-1] > 100
        self.results['cci_oversold'] = cci.iloc[-1] < -100
        self.results['cci_strong'] = abs(cci.iloc[-1]) > 100
        self.results['cci_neutral'] = -100 <= cci.iloc[-1] <= 100
    
    # ==================== 威廉指标 ====================
    def williams_system(self, period=14):
        """威廉指标 Williams %R"""
        highest = self.high.rolling(period).max()
        lowest = self.low.rolling(period).min()
        
        wr = -100 * (highest - self.close) / (highest - lowest)
        
        self.results['williams_r'] = round(wr.iloc[-1], 1)
        
        # 威廉信号
        self.results['williams_overbought'] = wr.iloc[-1] > -20  # > -20 超买
        self.results['williams_oversold'] = wr.iloc[-1] < -80   # < -80 超卖
        self.results['williams_mid'] = -80 < wr.iloc[-1] < -20
    
    # ==================== OBV系统 ====================
    def obv_system(self):
        """OBV能量潮"""
        obv = (np.sign(self.close.diff()) * self.volume).cumsum()
        
        self.results['obv'] = round(obv.iloc[-1], 0)
        self.results['obv_ma'] = round(obv.rolling(10).mean().iloc[-1], 0)
        self.results['obv_trend'] = 'rising' if obv.iloc[-1] > obv.iloc[-5] else 'falling'
        
        # OBV信号
        self.results['obv_bullish'] = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
        self.results['obv_divergence'] = self._detect_divergence(obv, 'obv')
    
    # ==================== MFI系统 ====================
    def mfi_system(self, period=14):
        """MFI资金流量指标"""
        tp = (self.high + self.low + self.close) / 3
        raw_mf = tp * self.volume
        
        mf_sign = np.where(tp > tp.shift(1), 1, -1)
        pos_mf = raw_mf.where(mf_sign > 0, 0).rolling(period).sum()
        neg_mf = raw_mf.where(mf_sign < 0, 0).rolling(period).sum()
        
        mr = pos_mf / neg_mf
        mfi = 100 - (100 / (1 + mr))
        
        self.results['mfi'] = round(mfi.iloc[-1], 1)
        
        # MFI信号
        self.results['mfi_overbought'] = mfi.iloc[-1] > 80  # 超买
        self.results['mfi_oversold'] = mfi.iloc[-1] < 20   # 超卖
        self.results['mfi_neutral'] = 20 <= mfi.iloc[-1] <= 80
        self.results['mfi_bullish'] = mfi.iloc[-1] > 50 and mfi.iloc[-1] > mfi.iloc[-5]
    
    # ==================== SAR系统 ====================
    def sar_system(self, accel=0.02, max_af=0.2):
        """SAR抛物线指标"""
        sar = self.close.copy()
        trend = [1]  # 1=上涨, -1=下跌
        
        for i in range(1, len(self.close)):
            if trend[-1] == 1:
                sar.iloc[i] = sar.iloc[i-1] + accel * (self.high.iloc[i-1] - sar.iloc[i-1])
                if self.low.iloc[i] < sar.iloc[i]:
                    trend.append(-1)
                    sar.iloc[i] = self.high.iloc[i-1]
                else:
                    trend.append(1)
            else:
                sar.iloc[i] = sar.iloc[i-1] + accel * (self.low.iloc[i-1] - sar.iloc[i-1])
                if self.high.iloc[i] > sar.iloc[i]:
                    trend.append(1)
                    sar.iloc[i] = self.low.iloc[i-1]
                else:
                    trend.append(-1)
        
        self.results['sar'] = round(sar.iloc[-1], 2)
        self.results['sar_trend'] = 'bullish' if trend[-1] == 1 else 'bearish'
        self.results['sar_price_cross'] = 'above' if self.close.iloc[-1] > sar.iloc[-1] else 'below'
    
    # ==================== VWAP系统 ====================
    def vwap_system(self):
        """VWAP成交量加权平均价"""
        tp = (self.high + self.low + self.close) / 3
        self.results['vwap'] = round((tp * self.volume).sum() / self.volume.sum(), 2)
        self.results['vwap_vs_price'] = 'above' if self.close.iloc[-1] > self.results['vwap'] else 'below'
    
    # ==================== 量价分析 ====================
    def volume_profile(self):
        """量价综合分析"""
        vol_ma5 = self.volume.rolling(5).mean().iloc[-1]
        vol_ma20 = self.volume.rolling(20).mean().iloc[-1]
        vol_now = self.volume.iloc[-1]
        
        self.results['volume'] = vol_now
        self.results['volume_ma5'] = vol_ma5
        self.results['volume_ma20'] = vol_ma20
        self.results['vol_ratio'] = round(vol_now / vol_ma5, 2) if vol_ma5 > 0 else 1
        
        # 量价信号
        self.results['volume_surge'] = self.results['vol_ratio'] > 1.5  # 放量
        self.results['volume_shrink'] = self.results['vol_ratio'] < 0.7  # 缩量
        self.results['volume_normal'] = 0.7 <= self.results['vol_ratio'] <= 1.5
        
        # 量价配合
        price_up = self.close.iloc[-1] > self.close.iloc[-2]
        vol_up = self.volume.iloc[-1] > self.volume.iloc[-2]
        self.results['price_volume_confirm'] = price_up == vol_up  # 价量配合
        
        # 上涨日放量/缩量
        if len(self.close) >= 5:
            recent_changes = self.close.tail(5).pct_change()
            up_days = (recent_changes > 0).sum()
            self.results['recent_up_days'] = up_days
    
    # ==================== 趋势强度 ====================
    def trend_strength(self):
        """趋势强度分析"""
        # ADX趋势强度
        adx = self.results.get('dmi_adx', 20)
        self.results['trend_strength'] = 'strong' if adx > 25 else ('moderate' if adx > 15 else 'weak')
        
        # 均线趋势
        if self.results.get('ma_bullish'):
            self.results['trend_direction'] = 'bullish'
        elif self.results.get('ma_bearish'):
            self.results['trend_direction'] = 'bearish'
        else:
            self.results['trend_direction'] = 'sideways'
        
        # 综合评分
        score = 0
        if self.results.get('ma_bullish'): score += 25
        if self.results.get('macd_bullish'): score += 20
        if self.results.get('rsi_neutral'): score += 15
        if self.results.get('dmi_strong_trend'): score += 20
        if self.results.get('volume_surge'): score += 10
        if self.results.get('sar_trend') == 'bullish': score += 10
        
        self.results['technical_score'] = min(100, score)
        self.results['technical_grade'] = 'A' if score >= 80 else ('B' if score >= 60 else ('C' if score >= 40 else 'D'))
    
    # ==================== 辅助函数 ====================
    def _detect_divergence(self, series, name):
        """检测背离 - 价格创新高但指标没有"""
        if len(series) < 20:
            return 'none'
        
        price_trend = self.close.iloc[-1] - self.close.iloc[-10]
        indicator_trend = series.iloc[-1] - series.iloc[-10]
        
        if price_trend > 0 and indicator_trend < 0:
            return 'bearish_divergence'  # 顶背离
        elif price_trend < 0 and indicator_trend > 0:
            return 'bullish_divergence'  # 底背离
        return 'none'


def r(value, min_val, max_val):
    """简单映射函数"""
    if max_val == min_val:
        return 50
    return (value - min_val) / (max_val - min_val) * 100


def analyze_stock_enhanced(code, name, days=60):
    """获取数据并计算增强指标"""
    import baostock as bs
    
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        symbol,
        'date,open,high,low,close,volume,pctChg',
        start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
        end_date='2026-04-09', frequency='d', adjustflag='2'
    )
    
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if len(data) < 30:
        return None
    
    df = pd.DataFrame(data, columns=rs.fields)
    df = df[df['close'] != '']
    
    ti = TechnicalIndicators(df)
    results = ti.calculate_all()
    
    # 额外计算
    closes = df['close'].values.astype(float)
    results['price'] = round(closes[-1], 2)
    results['pct_change'] = round(float(df['pctChg'].iloc[-1]), 2)
    results['gain_5d'] = round((closes[-1] / closes[-6] - 1) * 100, 2) if len(closes) >= 6 else 0
    results['gain_20d'] = round((closes[-1] / closes[-21] - 1) * 100, 2) if len(closes) >= 21 else 0
    
    return results


def print_enhanced_report(results, name, code):
    """打印增强技术分析报告"""
    print(f"\n{'='*70}")
    print(f"  📊 专业技术指标分析 - {name}({code})")
    print(f"{'='*70}")
    
    # 趋势判断
    print(f"\n📈 趋势系统")
    print(f"  方向: {results.get('trend_direction', 'N/A')} | 强度: {results.get('trend_strength', 'N/A')}")
    print(f"  综合评分: {results.get('technical_score', 0)} ({results.get('technical_grade', 'N')})")
    
    ma = "多头" if results.get('ma_bullish') else "空头" if results.get('ma_bearish') else "混乱"
    print(f"  均线系统: MA5={results.get('ma5','N/A')} MA10={results.get('ma10','N/A')} MA20={results.get('ma20','N/A')} → {ma}")
    
    macd_sig = "金叉↑" if results.get('macd_bullish') else "死叉↓" if results.get('macd_bearish') else "整理"
    macd_mom = results.get('macd_momentum', 'N/A')
    print(f"  MACD: {results.get('macd', 0):.4f} vs 信号{results.get('macd_signal', 0):.4f} | {macd_sig} | {macd_mom}")
    if results.get('macd_divergence') != 'none':
        print(f"  ⚠️ MACD背离: {results.get('macd_divergence')}")
    
    print(f"\n📊 摆动指标")
    rsi_zone = results.get('rsi_zone', 'N/A')
    rsi_emoji = "🔴" if rsi_zone == 'overbought' else ("🟢" if rsi_zone == 'oversold' else "🟡")
    print(f"  RSI(14): {results.get('rsi', 'N/A')} → {rsi_emoji} {rsi_zone}")
    print(f"  KDJ: K={results.get('kdj_k', 'N/A')} D={results.get('kdj_d', 'N/A')} J={results.get('kdj_j', 'N/A')}")
    if results.get('kdj_golden_cross'): print(f"  ⚠️ KDJ金叉")
    if results.get('kdj_death_cross'): print(f"  ⚠️ KDJ死叉")
    
    cci = results.get('cci', 0)
    cci_zone = "超买" if abs(cci) > 100 else "正常"
    print(f"  CCI: {cci} → {cci_zone}")
    
    wr = results.get('williams_r', 0)
    wr_zone = "超买" if wr > -20 else ("超卖" if wr < -80 else "正常")
    print(f"  威廉%R: {wr} → {wr_zone}")
    
    print(f"\n🎯 通道与支撑")
    bb_pos = results.get('bb_position', 50)
    bb_zone = "上轨" if bb_pos > 80 else ("下轨" if bb_pos < 20 else "中轨")
    print(f"  布林带: {results.get('bb_lower', 'N/A')} | {results.get('bb_mid', 'N/A')} | {results.get('bb_upper', 'N/A')}")
    print(f"  当前位置: {bb_pos}% ({bb_zone})")
    if results.get('bb_squeeze'): print(f"  ⚠️ 布林带收口，可能突破")
    if results.get('bb_expansion'): print(f"  📢 布林带开口，波动加大")
    
    print(f"\n💰 资金流向")
    obv = "流入" if results.get('obv_trend') == 'rising' else "流出"
    print(f"  OBV: {obv} | MFI={results.get('mfi', 'N/A')}")
    if results.get('mfi_overbought'): print(f"  ⚠️ MFI超买，资金可能退潮")
    if results.get('mfi_oversold'): print(f"  💎 MFI超卖，资金可能入场")
    
    print(f"\n📉 动能与波动")
    print(f"  ATR: {results.get('atr', 'N/A')} ({results.get('atr_percent', 'N')}%)")
    vol = "高" if results.get('volatility_high') else ("低" if results.get('volatility_low') else "正常")
    print(f"  波动率: {vol}")
    
    dmi_trend = "上涨" if results.get('dmi_plus_di', 0) > results.get('dmi_minus_di', 0) else "下跌"
    adx = results.get('dmi_adx', 0)
    print(f"  DMI: +DI={results.get('dmi_plus_di', 'N/A')} -DI={results.get('dmi_minus_di', 'N/A')} ADX={adx}")
    if results.get('dmi_strong_trend'): print(f"  📢 ADX>{25}，趋势明显")
    
    print(f"\n⚡ 量价分析")
    vol_ratio = results.get('vol_ratio', 1)
    vol_status = "放量↑" if vol_ratio > 1.2 else ("缩量↓" if vol_ratio < 0.8 else "正常")
    print(f"  成交量: {vol_status} (比率{vol_ratio})")
    if results.get('price_volume_confirm'): print(f"  ✅ 量价配合良好")
    
    print(f"\n🛡️ SAR抛物线")
    sar_trend = "上涨趋势" if results.get('sar_trend') == 'bullish' else "下跌趋势"
    print(f"  SAR: {results.get('sar', 'N/A')} | 价格{'高于' if results.get('sar_price_cross') == 'above' else '低于'}SAR → {sar_trend}")
    
    print(f"\n{'='*70}")
    
    # 综合信号汇总
    buy_signals = []
    sell_signals = []
    
    if results.get('ma_bullish'): buy_signals.append("均线多头")
    if results.get('macd_bullish'): buy_signals.append("MACD金叉")
    if results.get('kdj_golden_cross'): buy_signals.append("KDJ金叉")
    if results.get('dmi_bullish'): buy_signals.append("DMI上涨")
    if results.get('volume_surge'): buy_signals.append("放量上涨")
    if results.get('sar_trend') == 'bullish': buy_signals.append("SAR看涨")
    if results.get('rsi_zone') == 'oversold': buy_signals.append("RSI超卖")
    if results.get('mfi_oversold'): buy_signals.append("MFI超卖")
    if results.get('obv_divergence') == 'bullish_divergence': buy_signals.append("OBV底背离")
    
    if results.get('ma_bearish'): sell_signals.append("均线空头")
    if results.get('macd_bearish'): sell_signals.append("MACD死叉")
    if results.get('kdj_death_cross'): sell_signals.append("KDJ死叉")
    if results.get('rsi_zone') == 'overbought': sell_signals.append("RSI超买")
    if results.get('mfi_overbought'): sell_signals.append("MFI超买")
    if results.get('macd_divergence') == 'bearish_divergence': sell_signals.append("MACD顶背离")
    
    print(f"  ✅ 买入信号({len(buy_signals)}): {', '.join(buy_signals) if buy_signals else '无'}")
    print(f"  ❌ 卖出信号({len(sell_signals)}): {', '.join(sell_signals) if sell_signals else '无'}")
    print(f"  🎯 技术评分: {results.get('technical_score', 0)}/100 ({results.get('technical_grade', 'N')})")
    print(f"{'='*70}")


if __name__ == "__main__":
    # 测试
    code, name = "600519", "贵州茅台"
    results = analyze_stock_enhanced(code, name)
    if results:
        print_enhanced_report(results, name, code)
