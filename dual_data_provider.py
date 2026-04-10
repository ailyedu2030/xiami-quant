#!/usr/bin/env python3
"""
虾米量化系统 - 双数据源 v1.0
Dual Data Provider (Tushare + Baostock)

优势:
- Tushare: 个股日线/周线/财务
- Baostock: 指数数据/大盘状态

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import baostock as bs
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# ==================== 配置 ====================

TUSHARE_TOKEN = 'af23e8d670b3c1ff1584d1c37070b8ce9fb1e4d94e401bc150487ebc'

# ==================== 数据提供类 ====================

class DualDataProvider:
    """双数据源提供者"""
    
    def __init__(self):
        self.ts_pro = ts.pro_api(TUSHARE_TOKEN)
        self.bs_login = False
        self._login_baostock()
    
    def _login_baostock(self):
        """登录baostock"""
        try:
            self.bs_login = bs.login() is None
        except:
            self.bs_login = False
    
    def _logout_baostock(self):
        """登出baostock"""
        if self.bs_login:
            try:
                bs.logout()
            except:
                pass
    
    # ============ Tushare接口 ============
    
    def get_tushare_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线数据 (Tushare)
        code: 600519.SH 或 002371.SZ
        """
        try:
            df = self.ts_pro.daily(ts_code=code, start_date=start_date.replace('-', ''),
                                  end_date=end_date.replace('-', ''))
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Tushare日线失败 {code}: {e}")
            return pd.DataFrame()
    
    def get_tushare_weekly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取周线数据 (Tushare)"""
        try:
            df = self.ts_pro.weekly(ts_code=code, start_date=start_date.replace('-', ''),
                                  end_date=end_date.replace('-', ''))
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Tushare周线失败 {code}: {e}")
            return pd.DataFrame()
    
    def get_tushare_monthly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取月线数据 (Tushare)"""
        try:
            df = self.ts_pro.monthly(ts_code=code, start_date=start_date.replace('-', ''),
                                   end_date=end_date.replace('-', ''))
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Tushare月线失败 {code}: {e}")
            return pd.DataFrame()
    
    # ============ Baostock接口 ============
    
    def get_baostock_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线数据 (Baostock)
        code: sh.600519 或 sz.002371
        """
        try:
            rs = bs.query_history_k_data_plus(code,
                'date,open,high,low,close,volume,pctChg',
                start_date=start_date, end_date=end_date, frequency='d', adjustflag='2')
            
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            if data:
                df = pd.DataFrame(data, columns=rs.fields)
                for col in ['open','high','low','close','volume','pctChg']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Baostock日线失败 {code}: {e}")
            return pd.DataFrame()
    
    def get_index_data(self, index_code: str = 'sh.000001', 
                       start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取指数数据 (Baostock)
        index_code: sh.000001 (上证), sz.399001 (深证)
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        
        try:
            rs = bs.query_history_k_data_plus(index_code,
                'date,open,high,low,close,volume,pctChg',
                start_date=start_date, end_date=end_date, frequency='d')
            
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            if data:
                df = pd.DataFrame(data, columns=rs.fields)
                for col in ['open','high','low','close','volume','pctChg']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"获取指数失败: {e}")
            return pd.DataFrame()
    
    # ============ 统一接口 ============
    
    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        统一日线接口 - 优先Tushare
        """
        # 转换代码格式
        ts_code = self._to_ts_code(code)
        
        # 优先用Tushare
        df = self.get_tushare_daily(ts_code, start_date, end_date)
        
        if df.empty:
            # 备用baostock
            bs_code = self._to_baostock_code(code)
            df = self.get_baostock_daily(bs_code, start_date, end_date)
        
        return df
    
    def get_weekly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """统一周线接口"""
        ts_code = self._to_ts_code(code)
        return self.get_tushare_weekly(ts_code, start_date, end_date)
    
    def get_monthly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """统一月线接口"""
        ts_code = self._to_ts_code(code)
        return self.get_tushare_monthly(ts_code, start_date, end_date)
    
    def get_market_state(self) -> str:
        """
        判断市场状态 (Baostock)
        """
        df = self.get_index_data()
        
        if df.empty or len(df) < 60:
            return 'NEUTRAL'
        
        df = df.sort_values('date')
        ma20 = df['close'].rolling(20).mean()
        ma60 = df['close'].rolling(60).mean()
        
        latest = df.iloc[-1]
        latest_ma20 = ma20.iloc[-1]
        latest_ma60 = ma60.iloc[-1]
        
        if latest_ma20 > latest_ma60:
            return 'BULL'
        elif latest_ma20 < latest_ma60:
            return 'BEAR'
        return 'NEUTRAL'
    
    # ============ 工具方法 ============
    
    def _to_ts_code(self, code: str) -> str:
        """转换为Tushare格式"""
        if '.SH' in code or '.SZ' in code:
            return code.upper()
        
        if code.startswith('sh.'):
            return code.replace('sh.', '') + '.SH'
        elif code.startswith('sz.'):
            return code.replace('sz.', '') + '.SZ'
        
        if code.startswith('6'):
            return code + '.SH'
        elif code.startswith(('0', '3')):
            return code + '.SZ'
        
        return code
    
    def _to_baostock_code(self, code: str) -> str:
        """转换为Baostock格式"""
        if 'sh.' in code or 'sz.' in code:
            return code.lower()
        
        if '.SH' in code:
            return 'sh.' + code.replace('.SH', '')
        elif '.SZ' in code:
            return 'sz.' + code.replace('.SZ', '')
        
        if code.startswith('6'):
            return 'sh.' + code
        elif code.startswith(('0', '3')):
            return 'sz.' + code
        
        return code
    
    def __del__(self):
        self._logout_baostock()

# ==================== 技术指标计算 ====================

class TechnicalAnalyzer:
    """技术分析"""
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        if df.empty:
            return df
        
        df = df.copy()
        close = df['close'] if 'close' in df.columns else df.iloc[:, 4]  # fallback
        high = df['high'] if 'high' in df.columns else df.iloc[:, 2]
        low = df['low'] if 'low' in df.columns else df.iloc[:, 3]
        vol = df['vol'] if 'vol' in df.columns else (df['volume'] if 'volume' in df.columns else df.iloc[:, 5])
        
        # MA
        for n in [5, 10, 20, 60]:
            df[f'MA{n}'] = close.rolling(n).mean()
        
        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # RSI
        if len(close) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
        else:
            df['RSI'] = 50
        
        # KDJ
        if len(close) >= 9:
            low_n = low.rolling(9).min()
            high_n = high.rolling(9).max()
            rsv = (close - low_n) / (high_n - low_n) * 100
            df['K'] = rsv.ewm(com=2, adjust=False).mean()
            df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            df['J'] = 3 * df['K'] - 2 * df['D']
        
        # 布林带
        df['BB_mid'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['BB_upper'] = df['BB_mid'] + 2 * bb_std
        df['BB_lower'] = df['BB_mid'] - 2 * bb_std
        
        # ATR
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # 成交量均线
        df['VOL_MA5'] = vol.rolling(5).mean()
        df['VOL_MA20'] = vol.rolling(20).mean()
        
        return df
    
    @staticmethod
    def get_signals(df: pd.DataFrame) -> Dict:
        """获取信号"""
        if df.empty or len(df) < 2:
            return {'error': '数据不足'}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 趋势
        ma_trend = 'bullish' if latest.get('MA5', 0) > latest.get('MA20', 0) > latest.get('MA60', 0) else \
                   ('bearish' if latest.get('MA5', 0) < latest.get('MA20', 0) < latest.get('MA60', 0) else 'neutral')
        
        # MACD
        macd_hist = latest.get('MACD_hist', 0)
        prev_macd = prev.get('MACD_hist', 0)
        macd_signal = 'golden' if macd_hist > 0 and prev_macd <= 0 else \
                     ('dead' if macd_hist < 0 and prev_macd >= 0 else 'neutral')
        
        # RSI
        rsi = latest.get('RSI', 50)
        
        # KDJ
        kdj_signal = 'golden' if latest.get('K', 0) > latest.get('D', 0) and prev.get('K', 0) <= prev.get('D', 0) else \
                    ('dead' if latest.get('K', 0) < latest.get('D', 0) and prev.get('K', 0) >= prev.get('D', 0) else 'neutral')
        
        # 成交量
        vol_ratio = latest['vol'] / latest['VOL_MA20'] if latest.get('VOL_MA20', 0) > 0 else 1
        
        # 2560战法
        ma25 = latest.get('MA25', latest.get('MA5', 0))  # fallback
        ma25_prev = prev.get('MA25', prev.get('MA5', 0))
        ma25_up = ma25 > ma25_prev if pd.notna(ma25) and pd.notna(ma25_prev) else False
        
        vol_ma5 = latest.get('VOL_MA5', 0)
        vol_ma60 = latest.get('VOL_MA20', 0)
        vol_golden = vol_ma5 > vol_ma60 and prev.get('VOL_MA5', 0) <= prev.get('VOL_MA20', 0)
        
        return {
            'close': float(latest.get('close', 0)),
            'ma_trend': ma_trend,
            'macd_signal': macd_signal,
            'rsi': float(rsi) if pd.notna(rsi) else 50,
            'kdj_signal': kdj_signal,
            'vol_ratio': float(vol_ratio),
            'ma25_up': ma25_up,
            'vol_golden': vol_golden,
            'atr': float(latest.get('ATR', 0)) if pd.notna(latest.get('ATR')) else 0,
        }

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("双数据源测试 (Tushare + Baostock)")
    print("="*80)
    
    provider = DualDataProvider()
    analyzer = TechnicalAnalyzer()
    
    # 市场状态
    print("\n[市场状态]")
    state = provider.get_market_state()
    print(f"  当前: {state}")
    
    # 测试股票
    test_stocks = [
        ('600519.SH', '贵州茅台'),
        ('002371.SZ', '北方华创'),
        ('300750.SZ', '宁德时代'),
        ('000977.SZ', '浪潮信息'),
    ]
    
    print("\n[股票分析]")
    results = []
    
    for code, name in test_stocks:
        # 获取数据
        start = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        end = datetime.now().strftime('%Y-%m-%d')
        
        df = provider.get_daily(code, start, end)
        
        if df.empty:
            print(f"\n❌ {name}: 无数据")
            continue
        
        # 计算指标
        df = analyzer.calculate(df)
        signals = analyzer.get_signals(df)
        
        # 综合评分
        score = 50
        reasons = []
        
        if signals['ma_trend'] == 'bullish':
            score += 20
            reasons.append('均线多头')
        elif signals['ma_trend'] == 'bearish':
            score -= 15
            reasons.append('均线空头')
        
        if signals['macd_signal'] == 'golden':
            score += 15
            reasons.append('MACD金叉')
        elif signals['macd_signal'] == 'dead':
            score -= 10
            reasons.append('MACD死叉')
        
        if 40 <= signals['rsi'] <= 60:
            score += 10
            reasons.append(f'RSI健康({signals["rsi"]:.0f})')
        
        if signals['vol_ratio'] > 1.5:
            score += 10
            reasons.append(f'放量({signals["vol_ratio"]:.1f}x)')
        
        results.append({
            'name': name,
            'code': code,
            'close': signals['close'],
            'score': min(100, max(0, score)),
            'ma_trend': signals['ma_trend'],
            'macd': signals['macd_signal'],
            'rsi': signals['rsi'],
            'vol_ratio': signals['vol_ratio'],
            'reasons': reasons
        })
        
        emoji = "🟢" if score >= 65 else ("🟡" if score >= 45 else "🔴")
        print(f"\n{emoji} {name}")
        print(f"   收盘: {signals['close']:.2f}")
        print(f"   评分: {score} | MA:{signals['ma_trend']} | MACD:{signals['macd_signal']} | RSI:{signals['rsi']:.0f}")
        print(f"   理由: {', '.join(reasons)}")
    
    # 清理
    provider._logout_baostock()
    
    print("\n" + "="*80)
    print("✅ 双数据源测试完成")
    print("="*80)

if __name__ == "__main__":
    main()
