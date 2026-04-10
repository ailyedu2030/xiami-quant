#!/usr/bin/env python3
"""
虾米量化系统 - 板块轮动实时监控 v1.0
Sector Rotation Real-Time Monitor

核心功能：
1. 监控22只龙头股（11个板块，每板块2只）
2. 实时检测板块轮动信号
3. 捕捉政策热点、资金流向、技术突破
4. 第一时间推送买入信号

监控频率：
- 开盘前：09:00 生成当日重点关注
- 盘中：每30分钟扫描一次
- 尾盘：14:30 输出战法信号
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import baostock as bs
import pandas as pd
import numpy as np

# ==================== 配置 ====================

SECTORS_CONFIG = {
    'AI人工智能': [('sz.000977','浪潮信息'), ('sz.002230','科大讯飞')],
    '新能源汽车': [('sz.300750','宁德时代'), ('sz.002594','比亚迪')],
    '半导体': [('sh.688981','中芯国际'), ('sz.002371','北方华创')],
    '军工': [('sh.600760','中航沈飞'), ('sz.002025','航天电器')],
    '白酒消费': [('sh.600519','贵州茅台'), ('sz.000858','五粮液')],
    '银行': [('sh.600036','招商银行'), ('sz.000001','平安银行')],
    '创新药': [('sz.300760','迈瑞医疗'), ('sh.688180','君实生物')],
    '光伏': [('sh.601012','隆基绿能'), ('sz.002459','晶澳科技')],
    '5G通信': [('sh.600050','中国联通'), ('sz.000063','中兴通讯')],
    '券商': [('sh.600030','中信证券'), ('sh.600109','国金证券')],
    '消费电子': [('sz.000725','京东方A'), ('sz.002475','立讯精密')],
}

# 热点检测阈值（基于3个月回测优化）
THRESHOLDS = {
    'vol_ratio_alert': 1.5,      # 放量预警 (权重59.2%)
    'pct_change_alert': 3.0,     # 涨幅预警 (权重15.2%)
    'limit_up': 9.5,            # 涨停
    'breakout_ma20': 1.02,       # 突破MA20 (权重15.3%)
    'hot_sector_vol': 1.3,       # 板块放量
}

# ==================== 数据结构 ====================

@dataclass
class StockSnapshot:
    """个股快照"""
    code: str
    name: str
    sector: str
    price: float = 0.0
    pct_chg: float = 0.0
    vol_ratio: float = 1.0
    ma20_diff: float = 0.0     # 与MA20差距%
    trend: str = 'NEUTRAL'       # UP/DOWN/NEUTRAL
    volume: float = 0.0
    
@dataclass
class Alert:
    """警报"""
    timestamp: str
    alert_type: str             # BREAKOUT/HOT_SECTOR/LIMIT_UP/etc
    stock: str
    sector: str
    message: str
    priority: str               # HIGH/MEDIUM/LOW
    price: float
    pct_chg: float

@dataclass
class SectorSignal:
    """板块信号"""
    sector: str
    leader: str
    follower: str
    leader_pct: float
    follower_pct: float
    sector_momentum: float      # 板块动量
    hot_score: float           # 热度评分
    recommendation: str

# ==================== 监控引擎 ====================

class SectorRotationMonitor:
    """
    板块轮动监控引擎
    """
    
    def __init__(self):
        self.name = "板块轮动监控"
        self.version = "v1.0"
        self.data_path = '/Users/jackie/.openclaw/workspace/stock-research/all_sectors_monitor.json'
        
    def load_historical_data(self) -> Dict:
        """加载历史数据"""
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                return json.load(f)
        return {}
    
    def get_realtime_data(self) -> List[StockSnapshot]:
        """获取实时数据"""
        bs.login()
        
        snapshots = []
        
        for sector, stocks in SECTORS_CONFIG.items():
            for code, name in stocks:
                # 转换代码格式
                bs_code = code.replace('sz.', 'sz.').replace('sh.', 'sh.')
                
                rs = bs.query_history_k_data_plus(bs_code,
                    'date,open,high,low,close,volume,pctChg',
                    start_date=(datetime.now() - timedelta(days=25)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency='d', adjustflag='2')
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    for col in ['close','volume','pctChg']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    
                    # 计算指标
                    ma20 = df['close'].tail(20).mean()
                    vol_ma20 = df['volume'].tail(20).mean()
                    
                    vol_ratio = float(latest['volume']) / vol_ma20 if vol_ma20 > 0 else 1.0
                    ma20_diff = (float(latest['close']) - ma20) / ma20 * 100 if ma20 > 0 else 0
                    trend = 'UP' if float(latest['close']) > ma20 else 'DOWN'
                    
                    snapshots.append(StockSnapshot(
                        code=code,
                        name=name,
                        sector=sector,
                        price=float(latest['close']),
                        pct_chg=float(latest['pctChg']),
                        vol_ratio=vol_ratio,
                        ma20_diff=ma20_diff,
                        trend=trend,
                        volume=float(latest['volume'])
                    ))
        
        bs.logout()
        return snapshots
    
    def detect_alerts(self, snapshots: List[StockSnapshot]) -> List[Alert]:
        """检测警报"""
        alerts = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for snap in snapshots:
            # 涨停检测
            if snap.pct_chg > THRESHOLDS['limit_up']:
                alerts.append(Alert(
                    timestamp=now,
                    alert_type='LIMIT_UP',
                    stock=snap.name,
                    sector=snap.sector,
                    message=f'🚀 {snap.name}涨停！({snap.pct_chg:.1f}%)',
                    priority='HIGH',
                    price=snap.price,
                    pct_chg=snap.pct_chg
                ))
            
            # 放量突破检测
            elif snap.vol_ratio > THRESHOLDS['vol_ratio_alert'] and snap.trend == 'UP':
                alerts.append(Alert(
                    timestamp=now,
                    alert_type='BREAKOUT',
                    stock=snap.name,
                    sector=snap.sector,
                    message=f'📈 {snap.name}放量突破！量比{snap.vol_ratio:.1f}倍',
                    priority='HIGH',
                    price=snap.price,
                    pct_chg=snap.pct_chg
                ))
            
            # 异动检测
            elif snap.pct_chg > THRESHOLDS['pct_change_alert']:
                alerts.append(Alert(
                    timestamp=now,
                    alert_type='HOT',
                    stock=snap.name,
                    sector=snap.sector,
                    message=f'🔥 {snap.name}涨幅{snap.pct_chg:.1f}%，关注！',
                    priority='MEDIUM',
                    price=snap.price,
                    pct_chg=snap.pct_chg
                ))
            
            # 板块轮动信号
            elif snap.vol_ratio > 1.3 and snap.ma20_diff > 2:
                alerts.append(Alert(
                    timestamp=now,
                    alert_type='SECTOR_ROTATION',
                    stock=snap.name,
                    sector=snap.sector,
                    message=f'🔄 {snap.sector}板块异动，{snap.name}领涨',
                    priority='MEDIUM',
                    price=snap.price,
                    pct_chg=snap.pct_chg
                ))
        
        return alerts
    
    def analyze_sector_momentum(self, snapshots: List[StockSnapshot]) -> List[SectorSignal]:
        """分析板块动量"""
        sector_data = {}
        
        # 按板块分组
        for snap in snapshots:
            if snap.sector not in sector_data:
                sector_data[snap.sector] = []
            sector_data[snap.sector].append(snap)
        
        signals = []
        
        for sector, stocks in sector_data.items():
            if len(stocks) < 2:
                continue
            
            # 排序：涨的在前
            stocks.sort(key=lambda x: -x.pct_chg)
            
            leader = stocks[0]
            follower = stocks[1]
            
            # 板块动量 = 龙头涨幅 + 跟风幅度
            momentum = leader.pct_chg * 0.6 + follower.pct_chg * 0.4
            
            # 热度评分
            hot_score = (
                leader.vol_ratio * 30 +
                leader.pct_chg * 20 +
                (1 if leader.trend == 'UP' else 0) * 25 +
                follower.pct_chg * 15 +
                follower.vol_ratio * 10
            )
            
            # 推荐
            if momentum > 3 and hot_score > 80:
                rec = '🟢 强势买入'
            elif momentum > 1.5 and hot_score > 60:
                rec = '🟡 谨慎关注'
            elif momentum < -2:
                rec = '🔴 回避'
            else:
                rec = '⚪ 观望'
            
            signals.append(SectorSignal(
                sector=sector,
                leader=leader.name,
                follower=follower.name,
                leader_pct=leader.pct_chg,
                follower_pct=follower.pct_chg,
                sector_momentum=momentum,
                hot_score=hot_score,
                recommendation=rec
            ))
        
        # 按热度排序
        signals.sort(key=lambda x: -x.hot_score)
        return signals
    
    def generate_report(self, snapshots: List[StockSnapshot], alerts: List[Alert], signals: List[SectorSignal]):
        """生成监控报告"""
        
        print("\n" + "="*80)
        print(f"  🔴 板块轮动实时监控 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*80)
        
        # 高优先级警报
        high_alerts = [a for a in alerts if a.priority == 'HIGH']
        if high_alerts:
            print(f"\n🚨 高优先级警报 ({len(high_alerts)}个)")
            print("-" * 60)
            for a in high_alerts:
                print(f"  {a.message}")
        
        # 板块热度排名
        print(f"\n📊 板块热度排名")
        print("-" * 80)
        print(f"{'排名':<4} {'板块':<12} {'龙头':<10} {'涨幅':<8} {'跟风':<8} {'动量':<8} {'热度':<6} {'信号'}")
        print("-" * 80)
        
        for i, sig in enumerate(signals[:6]):
            print(f"{i+1:<4} {sig.sector:<12} {sig.leader:<10} {sig.leader_pct:>+6.1f}% {sig.follower_pct:>+6.1f}% {sig.sector_momentum:>+6.2f} {sig.hot_score:<6.0f} {sig.recommendation}")
        
        # 个股异动
        medium_alerts = [a for a in alerts if a.priority == 'MEDIUM']
        if medium_alerts:
            print(f"\n🔥 异动监控 ({len(medium_alerts)}个)")
            print("-" * 60)
            for a in medium_alerts[:5]:
                print(f"  {a.message}")
        
        # 操作建议
        print(f"\n" + "="*80)
        print("  🎯 操作建议")
        print("="*80)
        
        buy_signals = [s for s in signals if '🟢' in s.recommendation]
        if buy_signals:
            print("\n🟢 强势板块（可追涨）：")
            for s in buy_signals[:3]:
                print(f"  • {s.sector}: {s.leader} +{s.leader_pct:.1f}%")
        
        watch_signals = [s for s in signals if '🟡' in s.recommendation]
        if watch_signals:
            print("\n🟡 关注板块（等回调）：")
            for s in watch_signals[:3]:
                print(f"  • {s.sector}: {s.leader} +{s.leader_pct:.1f}%")
        
        avoid_signals = [s for s in signals if '🔴' in s.recommendation]
        if avoid_signals:
            print("\n🔴 回避板块：")
            for s in avoid_signals:
                print(f"  • {s.sector}: {s.leader} {s.leader_pct:.1f}%")
        
        print("\n" + "="*80)
        
        return signals[:3]  # 返回Top3
    
    def run_scan(self) -> Tuple[List[SectorSignal], List[Alert]]:
        """运行扫描"""
        print(f"\n{'🔍'*40}")
        print(f"  板块轮动扫描启动...")
        
        # 获取实时数据
        snapshots = self.get_realtime_data()
        print(f"  获取 {len(snapshots)} 只股票数据")
        
        # 检测警报
        alerts = self.detect_alerts(snapshots)
        print(f"  发现 {len(alerts)} 个警报")
        
        # 分析板块动量
        signals = self.analyze_sector_momentum(snapshots)
        
        # 生成报告
        top_signals = self.generate_report(snapshots, alerts, signals)
        
        return signals, alerts

    def save_scan_result(self, signals: List[SectorSignal], alerts: List[Alert]):
        """保存扫描结果"""
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'top_signals': [
                {
                    'sector': s.sector,
                    'leader': s.leader,
                    'leader_pct': s.leader_pct,
                    'momentum': s.sector_momentum,
                    'hot_score': s.hot_score,
                    'recommendation': s.recommendation
                } for s in signals[:5]
            ],
            'alerts': [
                {
                    'type': a.alert_type,
                    'stock': a.stock,
                    'sector': a.sector,
                    'message': a.message,
                    'priority': a.priority,
                    'pct_chg': a.pct_chg
                } for a in alerts if a.priority == 'HIGH'
            ]
        }
        
        path = '/Users/jackie/.openclaw/workspace/stock-research/scan_results.json'
        with open(path, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result


def main():
    """主函数"""
    monitor = SectorRotationMonitor()
    signals, alerts = monitor.run_scan()
    monitor.save_scan_result(signals, alerts)
    return signals, alerts


if __name__ == "__main__":
    main()
