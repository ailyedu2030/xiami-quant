#!/usr/bin/env python3
"""
热门板块追踪系统
永远聚焦市场热点，不追冷门股
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

# 热门板块定义（按资金关注度和政策导向）
HOT_SECTORS = {
    "AI人工智能": {
        "codes": ["002230", "002415", "000977", "603160", "688041"],
        "names": ["科大讯飞", "海康威视", "浪潮信息", "兆易创新", "海光信息"],
        "关注理由": "政策加持+产业趋势+业绩爆发",
        "热度": "🔥🔥🔥🔥🔥"
    },
    "新能源汽车": {
        "codes": ["300750", "002594", "300014", "002812"],
        "names": ["宁德时代", "比亚迪", "亿纬锂能", "恩捷股份"],
        "关注理由": "渗透率提升+海外扩张+技术领先",
        "热度": "🔥🔥🔥🔥"
    },
    "半导体": {
        "codes": ["688981", "688012", "603986", "002371"],
        "names": ["中芯国际", "中微公司", "兆易创新", "北方华创"],
        "关注理由": "国产替代+周期复苏+政策攻坚",
        "热度": "🔥🔥🔥🔥"
    },
    "白酒消费": {
        "codes": ["600519", "000858", "000568", "002304"],
        "names": ["贵州茅台", "五粮液", "泸州老窖", "洋河股份"],
        "关注理由": "防御性强+高ROE+品牌溢价",
        "热度": "🔥🔥"
    },
    "创新药": {
        "codes": ["300760", "688180", "300122", "000538"],
        "names": ["迈瑞医疗", "君实生物", "智飞生物", "云南白药"],
        "关注理由": "老龄化+创新周期+估值修复",
        "热度": "🔥🔥🔥"
    },
    "军工": {
        "codes": ["600760", "600893", "002025", "300699"],
        "names": ["中航沈飞", "航发动力", "航天电器", "光威复材"],
        "关注理由": "地缘风险+装备现代化+国企改革",
        "热度": "🔥🔥🔥"
    },
    "银行": {
        "codes": ["600036", "000001", "601318", "601166"],
        "names": ["招商银行", "平安银行", "中国平安", "兴业银行"],
        "关注理由": "高股息+估值低位+稳增长受益",
        "热度": "🔥"
    }
}

def get_realtime(code, name):
    """获取单只股票实时数据"""
    try:
        prefix = "sh" if code.startswith("6") else "sz"
        symbol = f"{prefix}.{code}"
        
        lg = bs.login()
        rs = bs.query_history_k_data_plus(
            symbol,
            'date,open,high,low,close,volume,pctChg',
            start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            end_date='2026-04-09', frequency='d', adjustflag='2'
        )
        data = []
        while rs.error_code == '0' and rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        
        if len(data) < 5:
            return None
        
        df = pd.DataFrame(data, columns=rs.fields)
        for col in ['open','high','low','close','volume','pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        
        closes = df['close'].values
        price = closes[-1]
        pct = df['pctChg'].iloc[-1]
        
        # 计算指标
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
        
        exp12 = df['close'].ewm(span=12, adjust=False).mean().iloc[-1]
        exp26 = df['close'].ewm(span=26, adjust=False).mean().iloc[-1]
        macd = exp12 - exp26
        
        vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
        vol_now = df['volume'].iloc[-1]
        vol_ratio = vol_now / vol_ma5 if vol_ma5 > 0 else 1
        
        gain_5d = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
        gain_20d = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
        
        return {
            "name": name,
            "code": code,
            "price": round(price, 2),
            "pct": round(pct, 2),
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "rsi": round(rsi, 1),
            "macd": round(macd, 2),
            "vol_ratio": round(vol_ratio, 2),
            "gain_5d": round(gain_5d, 2),
            "gain_20d": round(gain_20d, 2),
            "ma_bullish": ma5 > ma10 > ma20 and price > ma5,
            "macd_bullish": macd > 0,
            "volume_up": vol_ratio > 1.2
        }
    except Exception as e:
        return None


def analyze_hot_sectors():
    """分析所有热门板块"""
    print("\n" + "="*70)
    print("  🔥 虾米热门板块追踪系统")
    print(f"  分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70 + "\n")
    
    results = {}
    
    for sector_name, sector_info in HOT_SECTORS.items():
        print(f"\n📊 {sector_name} {sector_info['热度']}")
        print(f"   关注理由: {sector_info['关注理由']}")
        print("-" * 60)
        
        sector_stocks = []
        
        for code, name in zip(sector_info["codes"], sector_info["names"]):
            data = get_realtime(code, name)
            if data:
                sector_stocks.append(data)
                status = "🟢" if data["ma_bullish"] and data["macd_bullish"] else ("🟡" if data["ma_bullish"] or data["macd_bullish"] else "🔴")
                print(f"   {status} {name}({code}) {data['price']}元 {data['pct']:+.2f}% RSI={data['rsi']}")
            else:
                print(f"   ❌ {name}({code}) 数据获取失败")
        
        if sector_stocks:
            # 计算板块整体强度
            bullish_count = sum(1 for s in sector_stocks if s["ma_bullish"])
            macd_bullish_count = sum(1 for s in sector_stocks if s["macd_bullish"])
            avg_rsi = sum(s["rsi"] for s in sector_stocks) / len(sector_stocks)
            avg_gain = sum(s["gain_5d"] for s in sector_stocks) / len(sector_stocks)
            
            # 找出板块最强股
            best_stock = max(sector_stocks, key=lambda x: (
                x["ma_bullish"] * 30 + x["macd_bullish"] * 20 + 
                (50 if x["rsi"] < 70 else 0) +
                x["volume_up"] * 10 +
                x["gain_5d"]
            ))
            
            results[sector_name] = {
                "热度": sector_info["热度"],
                "理由": sector_info["关注理由"],
                "股票数": len(sector_stocks),
                "多头排列": bullish_count,
                "MACD强势": macd_bullish_count,
                "平均RSI": round(avg_rsi, 1),
                "平均涨幅": round(avg_gain, 2),
                "最强股": best_stock["name"],
                "最强股代码": best_stock["code"],
                "最强股评分": best_stock["macd_bullish"] * 50 + best_stock["ma_bullish"] * 30 + (best_stock["volume_up"] * 10) + (50 if 40 <= best_stock["rsi"] <= 60 else 0),
                "板块强度": "🟢强势" if bullish_count >= len(sector_stocks) * 0.6 else ("🟡分化" if bullish_count >= len(sector_stocks) * 0.3 else "🔴偏弱")
            }
    
    return results


def print_summary(results):
    """打印热门板块综合分析"""
    print("\n" + "="*70)
    print("  📈 热门板块综合排行榜")
    print("="*70 + "\n")
    
    # 按板块强度排序
    sorted_sectors = sorted(results.items(), key=lambda x: x[1]["多头排列"] * 10 + x[1]["MACD强势"] * 5 - (x[1]["平均RSI"] - 50), reverse=True)
    
    print(f"{'排名':<4} {'板块名称':<12} {'强度':<6} {'多头':<4} {'MACD':<4} {'RSI均':<6} {'5日涨幅':<8} {'最强股'}")
    print("-" * 70)
    
    for i, (name, data) in enumerate(sorted_sectors, 1):
        print(f"{i:<4} {name:<12} {data['板块强度']:<6} {data['多头排列']:<4} {data['MACD强势']:<4} {data['平均RSI']:<6} {data['平均涨幅']:>6}%   {data['最强股']}({data['最强股代码']})")
    
    print("\n" + "="*70)
    print("  🎯 今日重点关注")
    print("="*70)
    
    # 找出今日最佳机会
    best_opportunities = []
    for name, data in sorted_sectors:
        if data["板块强度"] != "🔴偏弱":
            best_opportunities.append((name, data))
    
    # TOP 3 板块
    print("\n🏆 今日最强势板块 TOP 3:")
    for i, (name, data) in enumerate(best_opportunities[:3], 1):
        print(f"  {i}. {name} - 多头排列{data['多头排列']}只，MACD强势{data['MACD强势']}只")
    
    # RSI健康的强势股
    print("\n💎 RSI健康（40-60）+ 技术强势股:")
    for name, data in sorted_sectors[:3]:
        print(f"  {name}: {data['最强股']}({data['最强股代码']})")
    
    print("\n" + "="*70)
    print("  ⚠️ 风险提示")
    print("="*70)
    print("  • RSI>70的股票追高风险大，注意回调")
    print("  • 热门板块轮动快，止损纪律要严格")
    print("  • 建议仓位管理，单只不超20%")
    print("  • 本分析仅供参考，不构成投资建议")
    print("="*70)


if __name__ == "__main__":
    results = analyze_hot_sectors()
    print_summary(results)
