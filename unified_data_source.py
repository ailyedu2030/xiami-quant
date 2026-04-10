#!/usr/bin/env python3
"""
虾米量化系统 - 统一数据源 v1.0
Unified Data Source

整合三大数据源:
- Tushare:  个股行情(日/周/月线)、复权因子、资金流向
- Baostock: 大盘指数(上证/深证/沪深300/创业板)
- Akshare:  新闻、龙虎榜、宏观数据

Author: 虾米 (Xiami)
Date: 2026-04-11
"""

import baostock as bs
import tushare as ts
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ==================== 配置 ====================

TUSHARE_TOKEN = "04e614b32dfcd8b9314458c58ed52e4690d1d3e95f648d946b538906"

# ==================== 主类 ====================

class UnifiedDataSource:
    """
    统一数据源管理器
    
    使用优先级:
    1. Tushare: 个股K线、复权因子、资金流向
    2. Baostock: 大盘指数
    3. Akshare: 新闻、龙虎榜、宏观数据
    """
    
    def __init__(self):
        # 初始化Tushare
        ts.set_token(TUSHARE_TOKEN)
        self.ts_pro = ts.pro_api()
        
        # 登录Baostock
        bs.login()
        
        self.bs_logged_in = True
        self.ak = ak
        
        print("✅ 统一数据源初始化完成")
    
    def __del__(self):
        """析构时登出"""
        if self.bs_logged_in:
            try:
                bs.logout()
            except:
                pass
    
    # ==================== Tushare接口 ====================
    
    def get_tushare_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线数据 (Tushare)
        code: 600519.SH 或 002371.SZ
        """
        try:
            df = self.ts_pro.daily(
                ts_code=code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
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
            df = self.ts_pro.weekly(
                ts_code=code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Tushare周线失败: {e}")
            return pd.DataFrame()
    
    def get_tushare_monthly(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取月线数据 (Tushare)"""
        try:
            df = self.ts_pro.monthly(
                ts_code=code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Tushare月线失败: {e}")
            return pd.DataFrame()
    
    def get_adj_factor(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取复权因子 (Tushare)"""
        try:
            df = self.ts_pro.adj_factor(
                ts_code=code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            if df is not None and len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"复权因子失败: {e}")
            return pd.DataFrame()
    
    def get_moneyflow_hsgt(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取沪深港通资金流向 (Tushare)"""
        try:
            df = self.ts_pro.moneyflow_hsgt(
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            if df is not None and len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"资金流向失败: {e}")
            return pd.DataFrame()
    
    # ==================== Baostock接口 ====================
    
    def get_index_daily(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指数日线 (Baostock)
        index_code: sh.000001, sz.399001, sh.000300, sz.399006
        """
        try:
            rs = bs.query_history_k_data_plus(
                index_code,
                "date,open,high,low,close,volume,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency='d'
            )
            
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            if data:
                df = pd.DataFrame(data, columns=rs.fields)
                for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"指数日线失败 {index_code}: {e}")
            return pd.DataFrame()
    
    def get_market_state(self) -> Tuple[str, float, float]:
        """
        获取大盘状态
        返回: (状态, MA20, MA60)
        """
        df = self.get_index_daily('sh.000001', 
            (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d')
        )
        
        if df.empty or len(df) < 60:
            return 'NEUTRAL', 0, 0
        
        df = df.sort_values('date')
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        current = df['close'].iloc[-1]
        
        if ma20 > ma60:
            state = 'BULL'
        elif ma20 < ma60:
            state = 'BEAR'
        else:
            state = 'NEUTRAL'
        
        return state, ma20, ma60
    
    def get_stock_daily_bs(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取个股日线 (Baostock备用)
        code: sh.600519 或 sz.002371
        """
        try:
            # 转换代码格式
            bs_code = self._to_baostock_code(code)
            
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustflag='2'
            )
            
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            if data:
                df = pd.DataFrame(data, columns=rs.fields)
                for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"Baostock个股失败 {code}: {e}")
            return pd.DataFrame()
    
    # ==================== Akshare接口 ====================
    
    def get_news(self, keyword: str = "A股", limit: int = 10) -> pd.DataFrame:
        """获取财经新闻 (Akshare)"""
        try:
            df = ak.stock_news_em(symbol=keyword)
            if df is not None and len(df) > 0:
                return df.head(limit)
            return pd.DataFrame()
        except Exception as e:
            print(f"新闻获取失败: {e}")
            return pd.DataFrame()
    
    def get_lhb_detail(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取龙虎榜明细 (Akshare)"""
        try:
            df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            if df is not None and len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"龙虎榜获取失败: {e}")
            return pd.DataFrame()
    
    def get_market_fund_flow(self) -> pd.DataFrame:
        """获取市场资金流向 (Akshare)"""
        try:
            df = ak.stock_market_fund_flow()
            if df is not None and len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"市场资金流失败: {e}")
            return pd.DataFrame()
    
    def get_macro_gdp(self) -> pd.DataFrame:
        """获取GDP数据 (Akshare)"""
        try:
            df = ak.macro_china_gdp()
            if df is not None and len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"GDP获取失败: {e}")
            return pd.DataFrame()
    
    def get_macro_cpi(self) -> pd.DataFrame:
        """获取CPI数据 (Akshare)"""
        try:
            df = ak.macro_china_cpi()
            if df is not None and len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"CPI获取失败: {e}")
            return pd.DataFrame()
    
    # ==================== 统一接口 ====================
    
    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        统一日线接口 - 优先Tushare
        """
        # 优先用Tushare
        ts_code = self._to_ts_code(code)
        df = self.get_tushare_daily(ts_code, start_date, end_date)
        
        if df.empty:
            # 备用Baostock
            df = self.get_stock_daily_bs(code, start_date, end_date)
        
        return df
    
    def get_index(self, start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        获取多个指数
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        
        indices = {
            '上证指数': 'sh.000001',
            '深证成指': 'sz.399001',
            '沪深300': 'sh.000300',
            '创业板': 'sz.399006',
        }
        
        result = {}
        for name, code in indices.items():
            df = self.get_index_daily(code, start_date, end_date)
            if not df.empty:
                result[name] = df
        
        return result
    
    # ==================== 工具方法 ====================
    
    def _to_ts_code(self, code: str) -> str:
        """转换为Tushare格式"""
        if '.SH' in code or '.SZ' in code:
            return code.upper()
        if code.startswith('sh.'):
            return code.replace('sh.', '') + '.SH'
        if code.startswith('sz.'):
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
        if '.SZ' in code:
            return 'sz.' + code.replace('.SZ', '')
        if code.startswith('6'):
            return 'sh.' + code
        elif code.startswith(('0', '3')):
            return 'sz.' + code
        return code

# ==================== 主程序测试 ====================

def main():
    print("="*80)
    print("统一数据源 - 完整测试")
    print("="*80)
    
    ds = UnifiedDataSource()
    
    # 1. 大盘状态
    print("\n[1] 大盘状态...")
    state, ma20, ma60 = ds.get_market_state()
    print(f"  状态: {state} | MA20: {ma20:.2f} | MA60: {ma60:.2f}")
    
    # 2. 指数数据
    print("\n[2] 主要指数...")
    indices = ds.get_index()
    for name, df in indices.items():
        if not df.empty:
            latest = df.iloc[-1]
            print(f"  {name}: {latest['close']:.2f} ({latest['pctChg']:+.2f}%)")
    
    # 3. 个股数据
    print("\n[3] 个股日线 (Tushare)...")
    df = ds.get_tushare_daily('600519.SH', '2026-04-01', '2026-04-10')
    if not df.empty:
        print(f"  贵州茅台: {len(df)} 条")
        print(f"  最新: {df.iloc[-1]['close']:.2f}")
    
    # 4. 新闻
    print("\n[4] 财经新闻 (Akshare)...")
    news = ds.get_news('A股', 5)
    if not news.empty:
        for _, row in news.head(3).iterrows():
            title = str(row.get('新闻标题', ''))[:40]
            print(f"  - {title}...")
    
    # 5. 资金流向
    print("\n[5] 市场资金流向 (Akshare)...")
    flow = ds.get_market_fund_flow()
    if not flow.empty:
        print(f"  {len(flow)} 条数据")
        print(flow.head(3))
    
    # 6. 龙虎榜
    print("\n[6] 龙虎榜明细 (Akshare)...")
    lhb = ds.get_lhb_detail('2026-04-01', '2026-04-10')
    if not lhb.empty:
        print(f"  {len(lhb)} 条数据")
    
    print("\n" + "="*80)
    print("✅ 统一数据源测试完成!")
    print("="*80)

if __name__ == "__main__":
    main()
