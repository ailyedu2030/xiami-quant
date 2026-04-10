#!/usr/bin/env python3
"""
全市场智能股票筛选系统 - 顺序处理版（避免并发过高）
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import json, os, sys

def get_all_stocks():
    lg = bs.login()
    rs = bs.query_all_stock(day='2026-04-09')
    stocks = []
    while rs.error_code == '0' and rs.next():
        row = rs.get_row_data()
        code, status, name = row[0], row[1], row[2]
        if code.startswith(('sh.6', 'sz.0', 'sz.3', 'bj.8', 'bj.4')) and status == '1':
            stocks.append({"code": code, "name": name})
    bs.logout()
    return stocks

def analyze(code, name):
    try:
        lg = bs.login()
        rs = bs.query_history_k_data_plus(
            code, 'date,open,high,low,close,volume,pctChg',
            start_date=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
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
        for col in ['open','high','low','close','volume','pctChg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        if len(df) < 20:
            return None
        closes = df['close'].values
        price = closes[-1]
        pct = df['pctChg'].iloc[-1]
        vol = df['volume'].iloc[-1]
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
        macd_signal = pd.Series([macd]).ewm(span=9, adjust=False).mean().iloc[-1]
        bb_mid = df['close'].rolling(20).mean().iloc[-1]
        ma_bullish = ma5 > ma10 > ma20 and price > ma5
        macd_cross = macd > macd_signal
        rsi_ok = 30 < rsi < 70
        vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
        vol_ok = vol >= 5000000 and vol > vol_ma5 * 1.2
        score = 0
        if ma_bullish: score += 30
        if price > ma5: score += 10
        if macd_cross: score += 20
        if macd > 0: score += 10
        if 40 <= rsi <= 60: score += 10
        elif rsi_ok: score += 5
        if pct > 2: score += 10
        elif pct > 0: score += 5
        if vol_ok: score += 10
        if price > bb_mid: score += 5
        gain_20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
        if gain_20 > 0: score += 5
        score = min(100, score)
        return {
            "code": code.split('.')[1], "name": name, "price": round(price,2),
            "pct": round(pct,2), "ma5": round(ma5,2), "ma10": round(ma10,2),
            "ma20": round(ma20,2), "rsi": round(rsi,1), "macd": round(macd,2),
            "macd_cross": macd_cross, "ma_bullish": ma_bullish, "rsi_ok": rsi_ok,
            "vol": vol, "vol_ok": vol_ok, "score": score, "gain_20": round(gain_20,2)
        }
    except:
        return None

if __name__ == "__main__":
    print("🔍 获取A股列表...")
    stocks = get_all_stocks()
    print(f"✅ 获取到 {len(stocks)} 只A股\n")
    
    qualified = []
    for i, s in enumerate(stocks):
        if i % 500 == 0:
            print(f"  已分析 {i}/{len(stocks)}...")
        r = analyze(s["code"], s["name"])
        if r and r["score"] >= 45 and 5 <= r["price"] <= 500 and r["rsi_ok"] and r["vol_ok"]:
            qualified.append(r)
    
    qualified.sort(key=lambda x: x["score"], reverse=True)
    top20 = qualified[:20]
    
    print(f"\n{'='*75}")
    print(f"  🏆 虾米智能选股 - 今日买入机会")
    print(f"{'='*75}")
    print(f"\n✅ 找到 {len(qualified)} 只符合条件，TOP 20 如下:\n")
    print(f"{'排名':<4} {'名称':<10} {'代码':<8} {'现价':<8} {'今日涨幅':<8} {'MA5':<8} {'RSI':<6} {'评分':<5} {'评价'}")
    print("-"*75)
    
    for i, s in enumerate(top20, 1):
        sig = "🟢强烈推荐" if s["score"]>=80 else ("🟡重点关注" if s["score"]>=70 else "⚪可关注")
        print(f"{i:<4} {s['name']:<10} {s['code']:<8} {s['price']:<8} {s['pct']:>5}%   {s['ma5']:<8} {s['rsi']:<6} {s['score']:<5} {sig}")
    
    print("-"*75)
    print(f"\n📈 TOP 10 推荐:")
    for i, s in enumerate(top20[:10], 1):
        print(f"  {i}. {s['name']}({s['code']}) {s['price']}元 {s['pct']:+.2f}% RSI={s['rsi']} 评分={s['score']}")
    
    # 保存
    os.makedirs("/Users/jackie/.openclaw/workspace/stock-research/reports", exist_ok=True)
    report_file = f"/Users/jackie/.openclaw/workspace/stock-research/reports/screener_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_file, 'w') as f:
        json.dump({"qualified": qualified[:100], "total": len(qualified)}, f, ensure_ascii=False, indent=2)
    print(f"\n📁 完整结果已保存: {report_file}")
    print(f"\n⚠️ 免责声明: 仅供参考，不构成投资建议")
