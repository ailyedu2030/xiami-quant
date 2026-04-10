#!/usr/bin/env python3
"""
虾米股票系统 - 持仓跟踪模块
记录持仓、跟踪表现、自动提醒止损

Author: 虾米 (Xiami)
Date: 2026-04-10
"""

import sys
sys.path.insert(0, '/Users/jackie/.openclaw/workspace/stock-research/')

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# 持仓数据文件
PORTFOLIO_FILE = '/Users/jackie/.openclaw/workspace/stock-research/portfolio.json'
TRADE_LOG_FILE = '/Users/jackie/.openclaw/workspace/stock-research/trade_log.json'


class Portfolio:
    """持仓管理器"""
    
    def __init__(self):
        self.positions = self._load_positions()
        self.trade_log = self._load_trade_log()
    
    def _load_positions(self) -> List[Dict]:
        """加载持仓"""
        if os.path.exists(PORTFOLIO_FILE):
            try:
                with open(PORTFOLIO_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _load_trade_log(self) -> List[Dict]:
        """加载交易记录"""
        if os.path.exists(TRADE_LOG_FILE):
            try:
                with open(TRADE_LOG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_positions(self):
        """保存持仓"""
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(self.positions, f, ensure_ascii=False, indent=2)
    
    def _save_trade_log(self):
        """保存交易记录"""
        with open(TRADE_LOG_FILE, 'w') as f:
            json.dump(self.trade_log, f, ensure_ascii=False, indent=2)
    
    def add_position(self, code: str, name: str, shares: int, 
                    entry_price: float, entry_date: str,
                    stop_loss: float, target: float,
                    strategy: str = '', notes: str = ''):
        """添加持仓"""
        position = {
            'id': len(self.positions) + 1,
            'code': code,
            'name': name,
            'shares': shares,
            'entry_price': entry_price,
            'entry_date': entry_date,
            'stop_loss': stop_loss,
            'target': target,
            'strategy': strategy,
            'notes': notes,
            'created_at': datetime.now().isoformat(),
        }
        self.positions.append(position)
        self._save_positions()
        
        # 记录交易
        self.record_trade('buy', code, name, shares, entry_price, entry_date, strategy)
        
        return position
    
    def remove_position(self, position_id: int, exit_price: float, 
                       exit_date: str, reason: str = ''):
        """平仓"""
        for i, pos in enumerate(self.positions):
            if pos['id'] == position_id:
                pos = self.positions.pop(i)
                
                # 记录交易
                self.record_trade('sell', pos['code'], pos['name'], 
                                pos['shares'], exit_price, exit_date, 
                                pos.get('strategy', ''), reason)
                
                # 计算盈亏
                pnl = (exit_price - pos['entry_price']) * pos['shares']
                pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price'] * 100
                
                self._save_positions()
                
                return {
                    'code': pos['code'],
                    'name': pos['name'],
                    'shares': pos['shares'],
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': reason,
                }
        return None
    
    def record_trade(self, action: str, code: str, name: str, 
                    shares: int, price: float, date: str,
                    strategy: str = '', reason: str = ''):
        """记录交易"""
        trade = {
            'action': action,
            'code': code,
            'name': name,
            'shares': shares,
            'price': price,
            'amount': shares * price,
            'date': date,
            'strategy': strategy,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
        }
        self.trade_log.append(trade)
        self._save_trade_log()
        return trade
    
    def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        return self.positions
    
    def update_current_prices(self, prices: Dict[str, float]):
        """更新当前价"""
        for pos in self.positions:
            code = pos['code']
            if code in prices:
                pos['current_price'] = prices[code]
                pos['current_value'] = prices[code] * pos['shares']
                pos['unrealized_pnl'] = (prices[code] - pos['entry_price']) * pos['shares']
                pos['unrealized_pnl_pct'] = (prices[code] - pos['entry_price']) / pos['entry_price'] * 100
                pos['updated_at'] = datetime.now().isoformat()
        
        self._save_positions()
    
    def check_stop_loss(self) -> List[Dict]:
        """检查需要止损的持仓"""
        alerts = []
        for pos in self.positions:
            current_price = pos.get('current_price', pos['entry_price'])
            
            if current_price < pos['stop_loss']:
                alerts.append({
                    'type': 'stop_loss',
                    'position_id': pos['id'],
                    'code': pos['code'],
                    'name': pos['name'],
                    'entry_price': pos['entry_price'],
                    'current_price': current_price,
                    'stop_loss': pos['stop_loss'],
                    'loss_pct': (current_price - pos['entry_price']) / pos['entry_price'] * 100,
                    'strategy': pos.get('strategy', ''),
                    'message': f"⚠️ 止损提醒: {pos['name']}({pos['code']}) 当前价{current_price}低于止损价{pos['stop_loss']}"
                })
            elif current_price >= pos['target']:
                alerts.append({
                    'type': 'target_reached',
                    'position_id': pos['id'],
                    'code': pos['code'],
                    'name': pos['name'],
                    'entry_price': pos['entry_price'],
                    'current_price': current_price,
                    'target': pos['target'],
                    'profit_pct': (current_price - pos['entry_price']) / pos['entry_price'] * 100,
                    'strategy': pos.get('strategy', ''),
                    'message': f"🎯 目标达成: {pos['name']}({pos['code']}) 已触及目标价{pos['target']}"
                })
        
        return alerts
    
    def get_performance_summary(self) -> Dict:
        """获取业绩汇总"""
        if not self.trade_log:
            return {
                'total_trades': 0,
                'total_invested': 0,
                'realized_pnl': 0,
                'open_positions': len(self.positions),
            }
        
        closed_trades = [t for t in self.trade_log if t['action'] == 'sell']
        buy_trades = [t for t in self.trade_log if t['action'] == 'buy']
        
        total_invested = sum(t['amount'] for t in buy_trades)
        realized_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        
        return {
            'total_trades': len(self.trade_log),
            'closed_trades': len(closed_trades),
            'open_positions': len(self.positions),
            'total_invested': total_invested,
            'realized_pnl': realized_pnl,
            'win_trades': len([t for t in closed_trades if t.get('pnl', 0) > 0]),
            'loss_trades': len([t for t in closed_trades if t.get('pnl', 0) <= 0]),
        }
    
    def print_portfolio_status(self):
        """打印持仓状态"""
        print(f"""
{'='*70}
📊 虾米持仓状态
{'='*70}""")
        
        if not self.positions:
            print("  暂无持仓")
        else:
            print(f"""
{'代码':<10} {'名称':<10} {'持仓':<6} {'成本':<10} {'现价':<10} {'盈亏':<12} {'止损':<10}
{'-'*70}""")
            
            for pos in self.positions:
                current = pos.get('current_price', '-')
                pnl = pos.get('unrealized_pnl', 0)
                pnl_pct = pos.get('unrealized_pnl_pct', 0)
                pnl_str = f"{pnl:+.2f} ({pnl_pct:+.1f}%)"
                
                print(f"{pos['code']:<10} {pos['name']:<10} {pos['shares']:<6} "
                      f"{pos['entry_price']:<10.2f} {current:<10.2f} {pnl_str:<12} "
                      f"{pos['stop_loss']:<10.2f}")
        
        summary = self.get_performance_summary()
        print(f"""
{'-'*70}
📈 累计表现
  总交易次数: {summary['total_trades']}
  已平仓: {summary['closed_trades']} | 持仓中: {summary['open_positions']}
  已实现盈亏: {summary['realized_pnl']:+.2f}
{'-'*70}""")
        
        # 检查止损
        alerts = self.check_stop_loss()
        if alerts:
            print("\n⚠️ 风险提醒:")
            for alert in alerts:
                print(f"  {alert['message']}")


# 全局实例
portfolio = Portfolio()


if __name__ == "__main__":
    # 测试
    print("测试持仓模块...")
    
    # 添加测试持仓
    portfolio.add_position(
        code='000977',
        name='浪潮信息',
        shares=1000,
        entry_price=65.0,
        entry_date='2026-04-09',
        stop_loss=60.0,
        target=75.0,
        strategy='2560战法',
        notes='AI热点'
    )
    
    # 模拟更新价格
    portfolio.update_current_prices({'000977': 67.5})
    
    # 打印状态
    portfolio.print_portfolio_status()
    
    # 检查止损
    alerts = portfolio.check_stop_loss()
    for alert in alerts:
        print(f"\n{alert['message']}")
