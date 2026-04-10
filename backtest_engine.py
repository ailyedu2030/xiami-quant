#!/usr/bin/env python3
"""
虾米股票系统 - 回测模块
验证策略有效性，统计胜率/盈亏比

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research/')

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.trades = []
        self.positions = []
        self.capital = initial_capital
        self.max_drawdown = 0
        self.peak_capital = initial_capital
    
    def reset(self):
        """重置回测状态"""
        self.trades = []
        self.positions = []
        self.capital = self.initial_capital
        self.max_drawdown = 0
        self.peak_capital = self.initial_capital
    
    def simulate_2560_strategy(self, df: pd.DataFrame, 
                                holding_period: int = 5,
                                stop_loss_pct: float = 0.08) -> Dict:
        """
        模拟2560战法回测
        
        买入条件:
        1. MA25向上
        2. VOL_MA5上穿VOL_MA60
        
        卖出条件:
        1. VOL_MA5下穿VOL_MA60
        2. 止损
        3. 持有N天后
        """
        self.reset()
        
        close = df['close']
        volume = df['volume']
        
        # 计算均线
        ma25 = close.rolling(25).mean()
        vol_ma5 = volume.rolling(5).mean()
        vol_ma60 = volume.rolling(60).mean()
        
        # 计算信号
        vol_golden = (vol_ma5 > vol_ma60) & (vol_ma5.shift(1) <= vol_ma60.shift(1))
        vol_dead = (vol_ma5 < vol_ma60) & (vol_ma5.shift(1) >= vol_ma60.shift(1))
        ma_up = ma25 > ma25.shift(1)
        
        buy_signal = vol_golden & ma_up
        
        trades = []
        position = None
        
        for i in range(60, len(df)):
            date = df['date'].iloc[i]
            price = close.iloc[i]
            
            if position is None:
                # 买入
                if buy_signal.iloc[i]:
                    shares = int(self.capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        cost = shares * price
                        position = {
                            'entry_date': date,
                            'entry_price': price,
                            'shares': shares,
                            'cost': cost,
                            'atr': self._calculate_atr_single(df, i, 14),
                        }
            else:
                # 卖出检查
                holding_days = i - df[df['date'] == position['entry_date']].index[0]
                exit_price = None
                exit_reason = None
                
                # 止损
                if price < position['entry_price'] * (1 - stop_loss_pct):
                    exit_price = price
                    exit_reason = 'stop_loss'
                # 死叉
                elif vol_dead.iloc[i]:
                    exit_price = price
                    exit_reason = 'vol_dead'
                # 持有到期
                elif holding_days >= holding_period:
                    exit_price = price
                    exit_reason = 'holding_period'
                
                if exit_price:
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
                    
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': date,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'holding_days': holding_days,
                        'reason': exit_reason,
                    })
                    
                    self.capital += pnl
                    position = None
        
        return self._analyze_results(trades, '2560战法')
    
    def simulate_breakout_strategy(self, df: pd.DataFrame,
                                     holding_period: int = 10,
                                     stop_loss_pct: float = 0.08) -> Dict:
        """
        模拟突破策略回测
        
        买入: 放量突破20日高点
        卖出: 止损 or 持有到期
        """
        self.reset()
        
        close = df['close']
        high = df['high']
        volume = df['volume']
        
        # 计算信号
        high_20 = high.rolling(20).max()
        vol_ma20 = volume.rolling(20).mean()
        
        breakout = (high > high_20.shift(1)) & (volume > vol_ma20 * 1.5)
        
        trades = []
        position = None
        
        for i in range(30, len(df)):
            date = df['date'].iloc[i]
            price = close.iloc[i]
            
            if position is None:
                if breakout.iloc[i]:
                    shares = int(self.capital * 0.95 / price / 100) * 100
                    if shares > 0:
                        position = {
                            'entry_date': date,
                            'entry_price': price,
                            'shares': shares,
                            'atr': self._calculate_atr_single(df, i, 14),
                        }
            else:
                holding_days = i - df[df['date'] == position['entry_date']].index[0]
                exit_price = None
                exit_reason = None
                
                # ATR止损
                atr_stop = position['entry_price'] - position['atr'] * 2
                if price < atr_stop:
                    exit_price = price
                    exit_reason = 'atr_stop'
                elif price < position['entry_price'] * (1 - stop_loss_pct):
                    exit_price = price
                    exit_reason = 'stop_loss'
                elif holding_days >= holding_period:
                    exit_price = price
                    exit_reason = 'holding_period'
                
                if exit_price:
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': date,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': (exit_price - position['entry_price']) / position['entry_price'] * 100,
                        'holding_days': holding_days,
                        'reason': exit_reason,
                    })
                    
                    self.capital += pnl
                    position = None
        
        return self._analyze_results(trades, '突破策略')
    
    def _calculate_atr_single(self, df: pd.DataFrame, idx: int, period: int = 14) -> float:
        """计算单点ATR"""
        if idx < period:
            return 0
        
        high = df['high'].iloc[idx-period:idx+1]
        low = df['low'].iloc[idx-period:idx+1]
        close = df['close'].iloc[idx-period:idx]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.mean()
    
    def _analyze_results(self, trades: List[Dict], strategy_name: str) -> Dict:
        """分析回测结果"""
        if not trades:
            return {
                'strategy': strategy_name,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_return': 0,
                'max_drawdown': 0,
            }
        
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in trades if t['pnl'] <= 0]
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        return {
            'strategy': strategy_name,
            'total_trades': len(trades),
            'win_trades': len(wins),
            'loss_trades': len(losses),
            'win_rate': len(wins) / len(trades) * 100,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0,
            'total_return': total_return,
            'final_capital': self.capital,
            'best_trade': max(t['pnl_pct'] for t in trades),
            'worst_trade': min(t['pnl_pct'] for t in trades),
            'avg_holding_days': np.mean([t['holding_days'] for t in trades]),
        }
    
    def run_full_backtest(self, code: str, start_date: str = '2020-01-01', 
                          end_date: str = '2026-04-09') -> Dict:
        """运行完整回测"""
        logger.info(f"开始回测 {code} ({start_date} ~ {end_date})")
        
        # 获取数据
        prefix = "sh" if code.startswith("6") else "sz"
        lg = bs.login()
        rs = bs.query_history_k_data_plus(
            f"{prefix}.{code}",
            'date,open,high,low,close,volume,pctChg',
            start_date=start_date,
            end_date=end_date,
            frequency='d',
            adjustflag='2'
        )
        
        data = []
        while rs.error_code == '0' and rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        
        if not data:
            return {'error': '无数据'}
        
        df = pd.DataFrame(data, columns=rs.fields)
        for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        
        logger.info(f"获取数据 {len(df)} 行")
        
        # 运行各策略回测
        results = {
            'code': code,
            'period': f"{start_date} ~ {end_date}",
            'initial_capital': self.initial_capital,
        }
        
        results['2560战法'] = self.simulate_2560_strategy(df)
        results['突破策略'] = self.simulate_breakout_strategy(df)
        
        return results


def print_backtest_report(results: Dict):
    """打印回测报告"""
    print(f"""
{'='*70}
📊 回测报告: {results.get('code', 'N/A')}
周期: {results.get('period', 'N/A')}
初始资金: {results.get('initial_capital', 0):,.2f}
{'='*70}""")
    
    for strategy_name, r in results.items():
        if strategy_name in ['code', 'period', 'initial_capital']:
            continue
        
        print(f"""
--- {r['strategy']} ---
  总交易次数: {r['total_trades']}
  盈利次数: {r['win_trades']} | 亏损次数: {r['loss_trades']}
  胜率: {r['win_rate']:.1f}%
  平均盈利: {r['avg_win']:.2f}元
  平均亏损: {r['avg_loss']:.2f}元
  盈亏比: {r['profit_factor']:.2f}
  总收益率: {r['total_return']:.2f}%
  最终资金: {r.get('final_capital', 0):,.2f}
  最佳交易: {r['best_trade']:.2f}%
  最差交易: {r['worst_trade']:.2f}%
  平均持仓: {r['avg_holding_days']:.1f}天""")


if __name__ == "__main__":
    print("运行回测...")
    
    engine = BacktestEngine(initial_capital=100000)
    
    # 回测浪潮信息
    results = engine.run_full_backtest("000977")
    
    print_backtest_report(results)
