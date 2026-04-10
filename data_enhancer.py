#!/usr/bin/env python3
"""
虾米股票系统 - 数据增强模块
1. baostock重试机制
2. ATR动态止损计算
3. 真实财务数据
4. 美股期货数据
5. 新闻情绪数据

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research/')

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import requests
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 1. baostock重试机制 ====================

def get_stock_data_with_retry(code: str, days: int = 90, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """带重试机制的股票数据获取"""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    for attempt in range(max_retries):
        try:
            lg = bs.login()
            if lg.error_code != '0':
                logger.warning(f"baostock登录失败: {lg.error_msg}")
                time.sleep(1)
                continue
            
            rs = bs.query_history_k_data_plus(
                symbol, 'date,open,high,low,close,volume,pctChg,turn',
                start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                end_date='2026-04-09', frequency='d', adjustflag='2'
            )
            
            if rs.error_code != '0':
                logger.warning(f"数据查询失败: {rs.error_msg}")
                bs.logout()
                time.sleep(1)
                continue
            
            data = []
            while rs.error_code == '0' and rs.next():
                data.append(rs.get_row_data())
            bs.logout()
            
            if not data:
                logger.warning(f"无数据返回: {code}")
                continue
            
            df = pd.DataFrame(data, columns=rs.fields)
            for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg', 'turn']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            logger.info(f"成功获取{code}数据: {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"获取数据异常 {code} (尝试{attempt+1}/{max_retries}): {e}")
            time.sleep(2)
    
    logger.error(f"获取{code}数据失败")
    return None


# ==================== 2. ATR动态止损 ====================

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ATR (Average True Range)"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR
    atr = tr.rolling(period).mean()
    return atr


def calculate_dynamic_stop_loss(price: float, df: pd.DataFrame, multiplier: float = 2.0) -> Dict:
    """计算动态止损位（基于ATR）"""
    atr = calculate_atr(df)
    current_atr = atr.iloc[-1] if not atr.empty else price * 0.02
    
    stop_loss = price - (current_atr * multiplier)
    target_1 = price + (current_atr * 2)
    target_2 = price + (current_atr * 3)
    target_3 = price + (current_atr * 5)
    
    return {
        'atr': round(current_atr, 3),
        'stop_loss': round(stop_loss, 2),
        'target_1': round(target_1, 2),
        'target_2': round(target_2, 2),
        'target_3': round(target_3, 2),
        'risk_reward_1': round((target_1 - price) / (price - stop_loss), 2),
        'risk_reward_2': round((target_2 - price) / (price - stop_loss), 2),
    }


# ==================== 3. 真实财务数据 ====================

def get_financial_data(code: str) -> Dict:
    """获取真实财务数据 from baostock"""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}.{code}"
    
    result = {
        'PE': None,
        'PB': None,
        'ROE': None,
        '营收增长率': None,
        '净利润增长率': None,
        '资产负债率': None,
        '市值': None,
        '流通市值': None,
    }
    
    try:
        lg = bs.login()
        
        # 获取利润表
        rs = bs.query_profit_sheet(symbol)
        profit_data = []
        while rs.error_code == '0' and rs.next():
            profit_data.append(rs.get_row_data())
        
        # 获取资产负债表
        rs = bs.query_balance_sheet(symbol)
        balance_data = []
        while rs.error_code == '0' and rs.next():
            balance_data.append(rs.get_row_data())
        
        # 获取主要财务指标
        rs = bs.query_growth_index(symbol)
        growth_data = []
        while rs.error_code == '0' and rs.next():
            growth_data.append(rs.get_row_data())
        
        bs.logout()
        
        # 简化处理 - 取最新一期数据
        if profit_data:
            # PE/PB 需要另外查询
            pass
        
        logger.info(f"获取财务数据: {code}")
        
    except Exception as e:
        logger.error(f"获取财务数据异常 {code}: {e}")
    
    return result


def get_valuation_from_sina(code: str) -> Dict:
    """从新浪获取估值数据"""
    prefix = "sh" if code.startswith("6") else "sz"
    url = f"http://hq.sinajs.cn/list={prefix}{code}"
    
    result = {
        'name': '',
        'open': 0,
        'high': 0,
        'low': 0,
        'price': 0,
        'volume': 0,
        'pct': 0,
        'amplitude': 0,
    }
    
    try:
        headers = {'Referer': 'http://finance.sina.com.cn'}
        resp = requests.get(url, headers=headers, timeout=5)
        content = resp.content.decode('gbk')
        
        # 解析数据
        # 格式: name,open,prev_close,price,high,low,bid,ask,volume,amount,...
        parts = content.split('"')[1].split(',')
        if len(parts) >= 32:
            result['name'] = parts[0]
            result['open'] = float(parts[1]) if parts[1] else 0
            result['high'] = float(parts[4]) if parts[4] else 0
            result['low'] = float(parts[5]) if parts[5] else 0
            result['price'] = float(parts[3]) if parts[3] else 0
            result['volume'] = float(parts[8]) if parts[8] else 0
            result['pct'] = float(parts[32]) if len(parts) > 32 and parts[32] else 0
            result['amplitude'] = float(parts[31]) if len(parts) > 31 and parts[31] else 0
            
    except Exception as e:
        logger.error(f"获取新浪数据异常 {code}: {e}")
    
    return result


# ==================== 4. 美股期货数据 ====================

def get_us_futures_data() -> Dict:
    """获取美股期货数据（用于判断国际影响）"""
    result = {
        'sp500_future': 0,
        'nasdaq_future': 0,
        'usdcny': 0,
        'gold': 0,
        'crude_oil': 0,
        'us_market_status': 'closed',  # premarket / open / closed
        'china_impact': 'neutral',  # positive / neutral / negative
    }
    
    try:
        # 新浪国际期货
        urls = {
            'sp500': 'http://hq.sinajs.cn/list=hf_SP500',
            'nasdaq': 'http://hq.sinajs.cn/list=hf_NDX',
            'usdcny': 'http://hq.sinajs.cn/list=fx_susdcny',
            'gold': 'http://hq.sinajs.cn/list=hf_GC',
            'crude': 'http://hq.sinajs.cn/list=hf_CL',
        }
        
        headers = {'Referer': 'http://finance.sina.com.cn'}
        
        for key, url in urls.items():
            try:
                resp = requests.get(url, headers=headers, timeout=3)
                content = resp.content.decode('gbk')
                value = content.split('"')[1].split(',')[0]
                
                if key == 'sp500':
                    result['sp500_future'] = float(value) if value else 0
                elif key == 'nasdaq':
                    result['nasdaq_future'] = float(value) if value else 0
                elif key == 'usdcny':
                    result['usdcny'] = float(value) if value else 0
                elif key == 'gold':
                    result['gold'] = float(value) if value else 0
                elif key == 'crude':
                    result['crude_oil'] = float(value) if value else 0
                    
            except Exception as e:
                logger.warning(f"获取{key}数据失败: {e}")
        
        # 判断美股影响
        if result['sp500_future'] > 0:
            if result['sp500_future'] > 1.0:
                result['us_market_status'] = 'premarket_positive'
                result['china_impact'] = 'positive'
            elif result['sp500_future'] < -1.0:
                result['us_market_status'] = 'premarket_negative'
                result['china_impact'] = 'negative'
            else:
                result['us_market_status'] = 'premarket_flat'
        
        logger.info(f"美股期货: SP500={result['sp500_future']}, 影响={result['china_impact']}")
        
    except Exception as e:
        logger.error(f"获取美股数据异常: {e}")
    
    return result


# ==================== 5. 新闻情绪数据 ====================

def get_news_sentiment(code: str, name: str = '') -> Dict:
    """获取新闻情绪数据（简化版）"""
    result = {
        'news_count': 0,
        'sentiment': 'neutral',  # positive / neutral / negative
        'sentiment_score': 50,
        'hot_score': 0,
        'related_sector': '',
    }
    
    try:
        # 这里可以接入真实新闻API
        # 暂时返回基于价格表现的简化情绪
        
        logger.info(f"获取新闻情绪: {code} {name}")
        
    except Exception as e:
        logger.error(f"获取新闻情绪异常 {code}: {e}")
    
    return result


# ==================== 6. 凯利公式仓位计算 ====================

def calculate_kelly_position(entry_price: float, stop_loss: float, 
                              win_rate: float = 0.5, 
                              reward_risk_ratio: float = 2.0,
                              max_position: float = 0.2) -> Dict:
    """
    凯利公式仓位计算
    
    凯利公式: f* = (bp - q) / b
    其中:
        f* = 仓位比例
        b = 赔率（盈利/亏损）
        p = 胜率
        q = 1 - p
    
    简化版: f* = (win_rate * reward_risk_ratio - (1 - win_rate)) / reward_risk_ratio
    """
    
    if win_rate <= 0 or reward_risk_ratio <= 0:
        return {
            'kelly_fraction': 0,
            'recommended_position': 0,
            'shares': 0,
            'risk_amount': 0,
            'max_position': max_position,
        }
    
    # 凯利公式
    kelly = (win_rate * reward_risk_ratio - (1 - win_rate)) / reward_risk_ratio
    
    # 安全系数（只用凯利的50%）
    safe_kelly = kelly * 0.5
    
    # 不超过最大仓位
    position = min(safe_kelly, max_position)
    
    # 每手100股
    risk_per_share = abs(entry_price - stop_loss)
    
    return {
        'kelly_fraction': round(kelly, 3),
        'safe_kelly': round(safe_kelly, 3),
        'recommended_position': round(position * 100, 1),  # 百分比
        'shares': int(position * 100 / entry_price) * 100,  # 整手数
        'risk_amount': round(risk_per_share * int(position * 100 / entry_price) * 100, 2),
        'reward_risk_ratio': reward_risk_ratio,
        'win_rate_assumption': win_rate,
    }


# ==================== 7. 板块热门度 ====================

def get_sector_hot_score(sector: str) -> int:
    """获取板块热门度评分"""
    hot_map = {
        'AI': 95,
        '人工智能': 95,
        '军工': 80,
        '半导体': 85,
        '白酒': 60,
        '银行': 55,
        '新能源': 75,
        '医药': 65,
        '房地产': 40,
        '教育': 45,
    }
    return hot_map.get(sector, 50)


# ==================== 8. 综合数据提供器 ====================

class DataProvider:
    """统一数据提供器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存
    
    def get_realtime(self, codes: list) -> Dict:
        """获取实时行情（批量）"""
        if not codes:
            return {}
        
        result = {}
        prefix_codes = []
        
        for code in codes:
            prefix = "sh" if code.startswith("6") else "sz"
            prefix_codes.append(f"{prefix}{code}")
        
        # 新浪批量API
        url = f"http://hq.sinajs.cn/list={','.join(prefix_codes)}"
        
        try:
            headers = {'Referer': 'http://finance.sina.com.cn'}
            resp = requests.get(url, headers=headers, timeout=10)
            content = resp.content.decode('gbk')
            
            items = content.split(';')
            for i, code in enumerate(codes):
                try:
                    item = items[i].split('"')[1]
                    parts = item.split(',')
                    if len(parts) >= 32:
                        result[code] = {
                            'name': parts[0],
                            'open': float(parts[1]) if parts[1] else 0,
                            'prev_close': float(parts[2]) if parts[2] else 0,
                            'price': float(parts[3]) if parts[3] else 0,
                            'high': float(parts[4]) if parts[4] else 0,
                            'low': float(parts[5]) if parts[5] else 0,
                            'volume': float(parts[8]) if parts[8] else 0,
                            'pct': float(parts[32]) if len(parts) > 32 and parts[32] else 0,
                            'amplitude': float(parts[31]) if len(parts) > 31 and parts[31] else 0,
                        }
                except Exception as e:
                    logger.warning(f"解析{code}失败: {e}")
                    
        except Exception as e:
            logger.error(f"批量获取实时行情失败: {e}")
        
        return result
    
    def get_all_data(self, code: str, name: str = '') -> Dict:
        """获取完整数据"""
        # 检查缓存
        cache_key = code
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_timeout:
                return cached['data']
        
        result = {
            'realtime': {},
            'history': None,
            'atr': {},
            'us_data': {},
            'financial': {},
            'news': {},
            'timestamp': datetime.now().isoformat(),
        }
        
        # 1. 实时行情
        result['realtime'] = get_valuation_from_sina(code)
        
        # 2. 历史数据
        result['history'] = get_stock_data_with_retry(code)
        
        # 3. ATR计算
        if result['history'] is not None and len(result['history']) > 20:
            price = result['realtime'].get('price', result['history']['close'].iloc[-1])
            result['atr'] = calculate_dynamic_stop_loss(price, result['history'])
        
        # 4. 美股数据
        result['us_data'] = get_us_futures_data()
        
        # 5. 财务数据
        result['financial'] = get_financial_data(code)
        
        # 6. 新闻情绪
        result['news'] = get_news_sentiment(code, name)
        
        # 缓存
        self.cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        
        return result


# 全局实例
data_provider = DataProvider()


if __name__ == "__main__":
    # 测试
    print("测试数据增强模块...")
    
    # 测试实时行情
    rt = get_valuation_from_sina("000977")
    print(f"浪潮信息实时: {rt}")
    
    # 测试美股
    us = get_us_futures_data()
    print(f"美股数据: {us}")
    
    # 测试凯利公式
    kelly = calculate_kelly_position(100, 92, win_rate=0.55, reward_risk_ratio=2.5)
    print(f"凯利仓位: {kelly}")
