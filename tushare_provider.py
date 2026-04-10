#!/usr/bin/env python3
"""
虾米量化系统 - Tushare数据层
Tushare Data Provider

Tushare优势:
- 日线/周线/月线数据
- 股票基础信息
- 财务数据(需权限)
- 资金流向(需权限)

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# ==================== Tushare配置 ====================

TOKEN = 'af23e8d670b3c1ff1584d1c37070b8ce9fb1e4d94e401bc150487ebc'
pro = ts.pro_api(TOKEN)

# ==================== 数据类 ====================

class TushareProvider:
    """Tushare数据提供者"""
    
    def __init__(self):
        self.connected = False
        self._test_connection()
    
    def _test_connection(self):
        """测试连接"""
        try:
            df = pro.stock_basic(exchange='', list_status='L', limit=1)
            self.connected = True
            print("✅ Tushare连接成功")
        except Exception as e:
            print(f"❌ Tushare连接失败: {e}")
            self.connected = False
    
    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线数据
        code: 600519.SH 或 002371.SZ
        """
        try:
            # 转换代码格式
            ts_code = self._to_ts_code(code)
            df = pro.daily(ts_code=ts_code, start_date=start_date.replace('-', ''), 
                          end_date=end_date.replace('-', ''))
            
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                # 重命名列为标准格式
                df = df.rename(columns={
                    'vol': 'volume',
                    'pct_chg': 'pctChg'
                })
                
                return df
            
            return pd.DataFrame()
        except Exception as e:
            print(f"获取日线失败 {code}: {e}")
            return pd.DataFrame()
    
    def get_weekly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取周线数据"""
        try:
            ts_code = self._to_ts_code(code)
            df = pro.weekly(ts_code=ts_code, start_date=start_date.replace('-', ''),
                           end_date=end_date.replace('-', ''))
            
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            
            return pd.DataFrame()
        except Exception as e:
            print(f"获取周线失败 {code}: {e}")
            return pd.DataFrame()
    
    def get_monthly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取月线数据"""
        try:
            ts_code = self._to_ts_code(code)
            df = pro.monthly(ts_code=ts_code, start_date=start_date.replace('-', ''),
                            end_date=end_date.replace('-', ''))
            
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            
            return pd.DataFrame()
        except Exception as e:
            print(f"获取月线失败 {code}: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取所有股票列表"""
        try:
            df = pro.stock_basic(exchange='', list_status='L', 
                                fields='ts_code,symbol,name,area,industry,market,list_date')
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_index_daily(self, index_code: str = '000001.SH', 
                       start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数日线 (需权限)"""
        # 备用方案：使用baostock
        print("⚠️ index_daily需权限，使用baostock备用")
        return pd.DataFrame()
    
    def get_moneyflow(self, code: str = None) -> pd.DataFrame:
        """获取资金流向 (需权限)"""
        print("⚠️ 资金流向需更高权限")
        return pd.DataFrame()
    
    def get_fina_indicator(self, code: str, start_date: str) -> pd.DataFrame:
        """获取财务指标 (需权限)"""
        print("⚠️ 财务指标需更高权限")
        return pd.DataFrame()
    
    def _to_ts_code(self, code: str) -> str:
        """转换代码格式"""
        # already in format 600519.SH or 002371.SZ
        if '.SH' in code or '.SZ' in code:
            return code.upper()
        
        # convert sh.600519 -> 600519.SH
        if code.startswith('sh.'):
            return code.replace('sh.', '') + '.SH'
        elif code.startswith('sz.'):
            return code.replace('sz.', '') + '.SZ'
        
        # assume Shanghai if 6xxxxx, Shenzhen if 0/3xxxxx
        if code.startswith('6'):
            return code + '.SH'
        elif code.startswith(('0', '3')):
            return code + '.SZ'
        
        return code
    
    def get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表"""
        try:
            df = pro.trade_cal(exchange='SSE', start_date=start_date.replace('-', ''),
                              end_date=end_date.replace('-', ''))
            df = df[df['is_open'] == 1]
            return df['cal_date'].tolist()
        except Exception as e:
            print(f"获取交易日失败: {e}")
            return []

# ==================== 数据增强功能 ====================

class DataEnhancer:
    """数据增强 - 使用Tushare数据"""
    
    def __init__(self):
        self.provider = TushareProvider()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # 收盘价
        close = df['close']
        volume = df['vol'] if 'vol' in df.columns else df['volume']
        
        # MA
        df['MA5'] = close.rolling(5).mean()
        df['MA10'] = close.rolling(10).mean()
        df['MA20'] = close.rolling(20).mean()
        df['MA60'] = close.rolling(60).mean()
        
        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # KDJ
        low14 = df['low'].rolling(14).min()
        high14 = df['high'].rolling(14).max()
        rsv = (close - low14) / (high14 - low14) * 100
        df['K'] = rsv.ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        # 布林带
        df['BB_mid'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['BB_upper'] = df['BB_mid'] + 2 * bb_std
        df['BB_lower'] = df['BB_mid'] - 2 * bb_std
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # 成交量均线
        df['VOL_MA5'] = volume.rolling(5).mean()
        df['VOL_MA20'] = volume.rolling(20).mean()
        
        return df
    
    def get_stock_signals(self, code: str, name: str = '') -> Dict:
        """获取股票完整信号"""
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')
        
        df = self.provider.get_daily(code, start, end)
        
        if df.empty:
            return {'error': f'无法获取 {code} 数据'}
        
        df = self.calculate_indicators(df)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 信号判断
        signals = {
            'code': code,
            'name': name,
            'date': str(latest['trade_date'])[:10],
            'close': float(latest['close']),
            'volume': float(latest['vol']) if 'vol' in latest else 0,
            
            # 趋势信号
            'ma_trend': 'bullish' if latest['MA5'] > latest['MA20'] > latest['MA60'] else 
                        ('bearish' if latest['MA5'] < latest['MA20'] < latest['MA60'] else 'neutral'),
            
            # MACD信号
            'macd_signal': 'golden' if latest['MACD_hist'] > 0 and prev['MACD_hist'] <= 0 else
                          ('dead' if latest['MACD_hist'] < 0 and prev['MACD_hist'] >= 0 else 'neutral'),
            
            # RSI信号
            'rsi': float(latest['RSI']) if pd.notna(latest.get('RSI')) else 50,
            
            # KDJ信号
            'kdj_signal': 'golden' if latest['K'] > latest['D'] and prev['K'] <= prev['D'] else
                         ('dead' if latest['K'] < latest['D'] and prev['K'] >= prev['D'] else 'neutral'),
            
            # 成交量信号
            'vol_ratio': float(latest['vol'] / latest['VOL_MA20']) if latest['VOL_MA20'] > 0 else 1,
            
            # 布林带位置
            'bb_position': (latest['close'] - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower']) 
                          if latest['BB_upper'] > latest['BB_lower'] else 0.5,
        }
        
        return signals

# ==================== 主程序 ====================

def main():
    print("="*80)
    print("Tushare 数据层测试")
    print("="*80)
    
    provider = TushareProvider()
    enhancer = DataEnhancer()
    
    # 测试股票
    test_stocks = [
        ('600519.SH', '贵州茅台'),
        ('002371.SZ', '北方华创'),
        ('300750.SZ', '宁德时代'),
    ]
    
    print("\n" + "-"*60)
    for code, name in test_stocks:
        print(f"\n📊 {name}({code})")
        signals = enhancer.get_stock_signals(code, name)
        
        if 'error' in signals:
            print(f"  ❌ {signals['error']}")
            continue
        
        print(f"  收盘: {signals['close']}")
        print(f"  MA趋势: {signals['ma_trend']}")
        print(f"  MACD: {signals['macd_signal']}")
        print(f"  RSI: {signals['rsi']:.1f}")
        print(f"  KDJ: {signals['kdj_signal']}")
        print(f"  量比: {signals['vol_ratio']:.2f}")

if __name__ == "__main__":
    main()
