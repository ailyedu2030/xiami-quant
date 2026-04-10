#!/usr/bin/env python3
"""
全市场智能股票筛选系统
从5000+A股中筛选今日值得买入的股票

筛选逻辑：
1. 趋势向上（价格在均线上方，多头排列）
2. 动能强劲（MACD金叉，成交量放大）
3. 未过度上涨（RSI < 70，避免追高）
4. 相对强度（强于大盘）
5. 底部支撑明确（布林带中轨支撑）
"""

import sys
import baostock as bs
import pandas as pd
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 筛选参数
SCREENER_PARAMS = {
    "min_price": 5,           # 最低股价（避免低价股陷阱）
    "max_price": 500,         # 最高股价
    "min_volume": 10000000,   # 最低日成交量（1000万）
    "max_rsI": 70,            # RSI上限（不过度追高）
    "min_rsI": 30,            # RSI下限（排除超卖）
    "min_gain_today": 0.5,    # 今日最小涨幅
    "ma_gap_ratio": 0.02,     # 均线多头：MA5至少高于MA10 2%
}

def get_all_stocks():
    """获取所有A股列表"""
    lg = bs.login()
    
    # 获取所有股票
    rs = bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
    
    stocks = []
    while rs.error_code == '0' and rs.next():
        row = rs.get_row_data()
        code = row[0]
        name = row[1]
        # 只保留A股（sh/sz/bj开头）
        if code.startswith(('sh.6', 'sz.0', 'sz.3', 'bj.8', 'bj.4')):
            stocks.append({"code": code, "name": name})
    
    bs.logout()
    return stocks

def format_code(std_code):
    """将 baostock 代码格式（如 sh.600519）转换为标准6位代码"""
    if '.' in std_code:
        return std_code.split('.')[1]
    return std_code

def get_prefix(std_code):
    """获取交易所前缀"""
    if std_code.startswith('sh.6') or std_code.startswith('sz.0') or std_code.startswith('sz.3'):
        return std_code.split('.')[0]
    return None

def analyze_stock_technical(std_code, name, days=60):
    """分析单只股票的技术面"""
    try:
        # 获取历史数据
        rs = bs.query_history_k_data_plus(
            std_code,
            'date,open,high,low,close,volume,pctChg',
            start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            frequency='d', adjustflag='2'
        )
        
        data = []
        while rs.error_code == '0' and rs.next():
            data.append(rs.get_row_data())
        
        if len(data) < 30:
            return None
        
        df = pd.DataFrame(data, columns=rs.fields)
        df = df[df['close'] != ''].copy()
        
        for col in ['open', 'high', 'low', 'close', 'volume', 'pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        
        if len(df) < 20:
            return None
        
        closes = df['close'].values
        last_price = closes[-1]
        last_pct = df['pctChg'].iloc[-1]
        volume = df['volume'].iloc[-1]
        
        # 计算均线
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_value = gain / loss
        rsi = (100 - (100 / (1 + rs_value))).iloc[-1]
        
        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = (exp12 - exp26).iloc[-1]
        signal = macd.ewm(span=9, adjust=False).mean().iloc[-1]
        
        # 布林带
        bb_mid = df['close'].rolling(20).mean().iloc[-1]
        bb_std = df['close'].rolling(20).std().iloc[-1]
        
        # 均线多头排列：MA5 > MA10 > MA20，且都在价格下方
        ma_bullish = ma5 > ma10 > ma20 and last_price > ma5
        
        # MACD金叉：MACD线从下方穿越信号线
        macd_cross_up = macd > signal
        
        # RSI在合理区间（30-70）
        rsi_ok = 30 < rsi < 70
        
        # 今日涨幅为正
        gain_ok = last_pct > 0
        
        # 价格在布林带中轨上方
        above_bb = last_price > bb_mid
        
        # 计算综合评分
        score = 0
        
        # 趋势分
        if ma_bullish: score += 30
        if last_price > ma5: score += 10
        
        # 动能分
        if macd_cross_up: score += 20
        if macd > 0: score += 10
        
        # RSI分
        if 40 < rsi < 60: score += 10  # 最佳区间
        elif rsi_ok: score += 5
        
        # 涨幅分
        if last_pct > 2: score += 10
        elif last_pct > 0: score += 5
        
        # 成交量分（放量）
        vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
        if volume > vol_ma5 * 1.2: score += 10
        
        # 布林带支撑分
        if above_bb: score += 5
        
        # 近期涨幅（20日）
        gain_20d = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
        if gain_20d > 0: score += 5
        
        return {
            "code": format_code(std_code),
            "name": name,
            "price": round(last_price, 2),
            "change_pct": round(last_pct, 2),
            "volume": volume,
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "rsi": round(rsi, 1),
            "macd": round(macd, 2),
            "signal": round(signal, 2),
            "ma_bullish": ma_bullish,
            "macd_cross_up": macd_cross_up,
            "rsi_ok": rsi_ok,
            "gain_ok": gain_ok,
            "above_bb": above_bb,
            "score": min(100, score),
            "gain_20d": round(gain_20d, 2)
        }
        
    except Exception as e:
        return None

def screen_stocks(all_stocks, top_n=20):
    """筛选符合条件的股票"""
    print(f"📊 开始筛选...（共 {len(all_stocks)} 只股票）")
    
    qualified = []
    count = 0
    
    # 批量处理，每批100只
    batch_size = 100
    
    for i in range(0, len(all_stocks), batch_size):
        batch = all_stocks[i:i+batch_size]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(analyze_stock_technical, s["code"], s["name"]): s
                for s in batch
            }
            
            for future in as_completed(futures):
                count += 1
                if count % 500 == 0:
                    print(f"  已分析 {count}/{len(all_stocks)} 只股票...")
                
                result = future.result()
                if result and result["score"] >= 40:
                    # 基础筛选条件
                    if (result["price"] >= SCREENER_PARAMS["min_price"] and
                        result["price"] <= SCREENER_PARAMS["max_price"] and
                        result["rsi_ok"] and
                        result["gain_ok"] and
                        result["volume"] >= SCREENER_PARAMS["min_volume"]):
                        qualified.append(result)
        
        print(f"  完成 {min(i+batch_size, len(all_stocks))}/{len(all_stocks)}")
    
    # 按评分排序
    qualified.sort(key=lambda x: x["score"], reverse=True)
    
    return qualified[:top_n]

def print_report(qualified_stocks):
    """打印筛选报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    print(f"\n{'='*70}")
    print(f"  🏆 虾米智能选股 - 今日买入机会")
    print(f"  筛选时间: {now}")
    print(f"  筛选条件: 趋势向上 + 动能强劲 + RSI健康 + 放量")
    print(f"{'='*70}")
    
    if not qualified_stocks:
        print("\n❌ 今日暂无符合条件的股票")
        print("💡 建议：市场整体偏弱，等待更好的机会")
        return
    
    print(f"\n✅ 找到 {len(qualified_stocks)} 只符合条件的股票\n")
    
    print(f"{'排名':<4} {'股票':<10} {'代码':<8} {'现价':<8} {'今日涨幅':<8} {'MA状态':<10} {'MACD':<8} {'RSI':<6} {'评分':<6} {'综合评价'}")
    print("-" * 100)
    
    for i, s in enumerate(qualified_stocks, 1):
        # MA状态
        ma_status = "多头排列" if s["ma_bullish"] else "均线混乱"
        
        # MACD状态
        macd_status = "金叉" if s["macd_cross_up"] else "整理中"
        
        # RSI评价
        rsi = s["rsi"]
        rsi_eval = "正常" if 40 <= rsi <= 60 else ("偏低" if rsi < 40 else "偏高")
        
        # 综合评价
        score = s["score"]
        if score >= 80:
            grade = "⭐⭐⭐⭐⭐ 强烈推荐"
        elif score >= 70:
            grade = "⭐⭐⭐⭐ 重点关注"
        elif score >= 60:
            grade = "⭐⭐⭐ 可以关注"
        else:
            grade = "⭐⭐ 谨慎参与"
        
        print(f"{i:<4} {s['name']:<10} {s['code']:<8} {s['price']:<8} {s['change_pct']:>6}%   {ma_status:<10} {macd_status:<8} {rsi:.1f}({rsi_eval})  {score:<6} {grade}")
    
    print("-" * 100)
    
    # 按行业分类
    print(f"\n📈 强势板块分布:")
    
    # 取前10只分析
    top10 = qualified_stocks[:10]
    print(f"\n  TOP 10 推荐:")
    for i, s in enumerate(top10, 1):
        print(f"  {i}. {s['name']}({s['code']}) - {s['price']}元 ({s['change_pct']:+.2f}%) | 评分:{s['score']}")
    
    # 风险提示
    print(f"\n{'='*70}")
    print(f"  ⚠️ 风险提示")
    print(f"{'='*70}")
    print(f"  1. 技术面选股仅供参考，不构成投资建议")
    print(f"  2. 建议控制仓位，单只股票不超过总仓位20%")
    print(f"  3. 务必设置止损位（建议8-10%）")
    print(f"  4. RSI>60的股票追高风险较大，请谨慎")
    print(f"  5. 近期涨幅过大(>10%)的股票注意回调风险")
    print(f"{'='*70}")
    
    # 保存报告
    report = {
        "筛选时间": now,
        "筛选条件": SCREENER_PARAMS,
        "结果数量": len(qualified_stocks),
        "股票列表": qualified_stocks
    }
    
    import os
    report_dir = os.path.dirname(os.path.abspath(__file__)) + "/reports"
    os.makedirs(report_dir, exist_ok=True)
    
    report_file = f"{report_dir}/screener_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 完整报告已保存: {report_file}")


if __name__ == "__main__":
    print(f"\n🔍 正在获取A股列表...")
    all_stocks = get_all_stocks()
    print(f"✅ 获取到 {len(all_stocks)} 只A股\n")
    
    if not all_stocks:
        print("❌ 获取股票列表失败")
        sys.exit(1)
    
    qualified = screen_stocks(all_stocks, top_n=20)
    print_report(qualified)
