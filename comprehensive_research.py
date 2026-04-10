#!/usr/bin/env python3
"""
虾米量化系统 - 综合研究引擎
Comprehensive Research Engine

研究内容:
1. 市场状态识别 (Market Regime)
2. Beta分析 (个股与大盘相关性)
3. 波动率聚类 (Volatility Clustering)
4. 机构资金流向 (Institutional Flow)
5. 凯利公式仓位 (Kelly Criterion)
6. 相关性风险 (Correlation Risk)
7. 尾部风险 (Tail Risk / VaR)
8. 最大回撤分析 (Max Drawdown)
9. 交易成本分析 (Transaction Costs)
10. 多时间框架共振 (Multi-Timeframe)
11. 过拟合检验 (Overfitting Check)
12. 事件驱动分析 (Event-Driven)
"""

import baostock as bs
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

# ==================== 配置 ====================

STOCKS = [
    ('sz.002812', '恩捷股份', '新能源'),
    ('sz.002371', '北方华创', '半导体'),
    ('sz.002025', '航天电器', '军工'),
    ('sh.600309', '万华化学', '化工'),
    ('sz.300751', '迈为股份', '光伏设备'),
    ('sh.603259', '药明康德', '医药外包'),
    ('sz.300760', '迈瑞医疗', '医疗器械'),
    ('sh.600519', '贵州茅台', '白酒'),
    ('sh.600887', '伊利股份', '乳业'),
    ('sh.688012', '中微公司', '半导体'),
    ('sz.300750', '宁德时代', '新能源'),
    ('sz.002594', '比亚迪', '新能源'),
    ('sh.600036', '招商银行', '银行'),
    ('sh.600030', '中信证券', '券商'),
    ('sz.000063', '中兴通讯', '通信'),
]

START_DATE = '2025-10-01'
END_DATE = '2026-04-10'

# ==================== 工具函数 ====================

def get_stock_data(code, start, end):
    """获取股票数据"""
    rs = bs.query_history_k_data_plus(code,
        'date,open,high,low,close,volume,pctChg',
        start_date=start, end_date=end, frequency='d', adjustflag='2')
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    if not data_list:
        return None
    df = pd.DataFrame(data_list, columns=rs.fields)
    for col in ['open','high','low','close','volume','pctChg']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def get_index_data():
    """获取上证指数数据"""
    return get_stock_data('sh.000001', START_DATE, END_DATE)

# ==================== 研究1: 市场状态识别 ====================

def analyze_market_regime(index_df):
    """
    分析大盘状态
    返回: 当前状态, 状态持续天数, 状态切换点
    """
    index_df = index_df.copy()
    index_df['MA20'] = index_df['close'].rolling(20).mean()
    index_df['MA60'] = index_df['close'].rolling(60).mean()
    
    # 状态: MA20 > MA60 = 牛市, 否则 = 熊市
    index_df['regime'] = np.where(index_df['MA20'] > index_df['MA60'], 'BULL', 'BEAR')
    
    # 当前状态
    current_regime = index_df['regime'].iloc[-1]
    
    # 状态持续天数
    regime_days = 0
    for i in range(len(index_df)-1, -1, -1):
        if index_df['regime'].iloc[i] == current_regime:
            regime_days += 1
        else:
            break
    
    # 最近切换点
    switch_points = []
    for i in range(1, len(index_df)):
        if index_df['regime'].iloc[i] != index_df['regime'].iloc[i-1]:
            switch_points.append({
                'date': index_df['date'].iloc[i],
                'from': index_df['regime'].iloc[i-1],
                'to': index_df['regime'].iloc[i]
            })
    
    # 计算各状态胜率
    bull_signals = 0
    bull_wins = 0
    bear_signals = 0
    bear_wins = 0
    
    return {
        'current_regime': current_regime,
        'regime_days': regime_days,
        'bull_days': (index_df['regime'] == 'BULL').sum(),
        'bear_days': (index_df['regime'] == 'BEAR').sum(),
        'recent_switches': switch_points[-5:] if switch_points else []
    }

# ==================== 研究2: Beta分析 ====================

def analyze_beta(stock_df, index_df):
    """
    计算个股Beta值
    Beta = Cov(stock, index) / Var(index)
    Beta > 1 表示波动大于大盘
    """
    # 合并数据
    merged = pd.merge(
        stock_df[['date', 'pctChg']].rename(columns={'pctChg': 'stock_pct'}),
        index_df[['date', 'pctChg']].rename(columns={'pctChg': 'index_pct'}),
        on='date', how='inner'
    )
    
    if len(merged) < 30:
        return None
    
    # 计算Beta
    covariance = np.cov(merged['stock_pct'].tail(60), merged['index_pct'].tail(60))[0][1]
    index_var = np.var(merged['index_pct'].tail(60))
    
    beta = covariance / index_var if index_var != 0 else 1.0
    
    # 计算Alpha (年化超额收益)
    stock_return = merged['stock_pct'].mean() * 250
    index_return = merged['index_pct'].mean() * 250
    alpha = stock_return - beta * index_return
    
    # 计算相关系数
    correlation = np.corrcoef(merged['stock_pct'].tail(60), merged['index_pct'].tail(60))[0][1]
    
    return {
        'beta': round(beta, 2),
        'alpha': round(alpha, 4),
        'correlation': round(correlation, 2),
        'interpretation': '高Beta' if beta > 1.2 else ('低Beta' if beta < 0.8 else '中性')
    }

# ==================== 研究3: 波动率聚类 ====================

def analyze_volatility(stock_df):
    """
    分析个股波动率
    识别高波动期和低波动期
    """
    stock_df = stock_df.copy()
    stock_df['volatility_20'] = stock_df['pctChg'].rolling(20).std()
    stock_df['volatility_60'] = stock_df['pctChg'].rolling(60).std()
    
    # 当前波动率
    current_vol = stock_df['volatility_20'].iloc[-1]
    avg_vol = stock_df['volatility_60'].iloc[-1]
    
    # 波动率状态
    vol_ratio = current_vol / avg_vol if avg_vol != 0 else 1
    
    # 计算ATR (Average True Range)
    stock_df['TR'] = np.maximum(
        stock_df['high'] - stock_df['low'],
        np.maximum(
            abs(stock_df['high'] - stock_df['close'].shift(1)),
            abs(stock_df['low'] - stock_df['close'].shift(1))
        )
    )
    stock_df['ATR'] = stock_df['TR'].rolling(14).mean()
    
    current_atr = stock_df['ATR'].iloc[-1]
    current_price = stock_df['close'].iloc[-1]
    atr_pct = current_atr / current_price * 100 if current_price != 0 else 0
    
    return {
        'current_volatility': round(current_vol * 100, 2),
        'avg_volatility': round(avg_vol * 100, 2),
        'vol_ratio': round(vol_ratio, 2),
        'atr': round(current_atr, 2),
        'atr_pct': round(atr_pct, 2),
        'status': '高波动' if vol_ratio > 1.3 else ('低波动' if vol_ratio < 0.7 else '正常')
    }

# ==================== 研究4: 凯利公式仓位 ====================

def calculate_kelly_position(win_rate, avg_win, avg_loss):
    """
    计算凯利公式最优仓位
    Kelly % = (p × b - q) / b
    其中 p = 胜率, q = 1-p, b = 赔率
    """
    if avg_loss == 0:
        return 0
    
    p = win_rate
    q = 1 - win_rate
    b = avg_win / abs(avg_loss)  # 赔率
    
    kelly = (p * b - q) / b if b != 0 else 0
    
    # 安全系数 = Kelly * 0.5 (只使用一半)
    safe_kelly = kelly * 0.5
    
    # 最大仓位限制
    max_position = min(safe_kelly, 0.25)  # 最高25%
    
    return {
        'kelly_pct': round(kelly * 100, 1),
        'safe_kelly_pct': round(safe_kelly * 100, 1),
        'max_position_pct': round(max_position * 100, 1),
        'recommendation': '轻仓(10%)' if max_position < 0.15 else ('标准仓(20%)' if max_position < 0.2 else '满仓(25%)')
    }

# ==================== 研究5: 相关性分析 ====================

def analyze_correlations(stock_dfs):
    """
    计算股票之间的相关性
    用于分散化投资
    """
    # 获取收盘价
    prices = pd.DataFrame()
    for code, name, sector in STOCKS[:10]:  # 取前10只
        df = stock_dfs.get(code)
        if df is not None:
            prices[name] = df['close'].values
    
    if prices.empty or len(prices) < 30:
        return None
    
    # 计算收益率相关性
    returns = prices.pct_change().dropna()
    corr_matrix = returns.corr()
    
    # 找出高相关股票对 (可能集中风险)
    high_corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr = corr_matrix.iloc[i, j]
            if abs(corr) > 0.7:
                high_corr_pairs.append({
                    'stock1': corr_matrix.columns[i],
                    'stock2': corr_matrix.columns[j],
                    'correlation': round(corr, 2)
                })
    
    return {
        'high_corr_pairs': high_corr_pairs,
        'avg_correlation': round(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].mean(), 2)
    }

# ==================== 研究6: VaR分析 (尾部风险) ====================

def analyze_var(stock_df, confidence=0.95):
    """
    计算VaR (Value at Risk)
    在给定置信度下的最大损失
    """
    returns = stock_df['pctChg'].dropna()
    
    if len(returns) < 30:
        return None
    
    # 历史模拟法
    var_95 = np.percentile(returns, (1 - confidence) * 100)
    cvar_95 = returns[returns <= var_95].mean()  # Expected Shortfall
    
    # 最大单日损失
    max_loss = returns.min()
    
    # 平均损失(负收益日)
    neg_returns = returns[returns < 0]
    avg_loss = neg_returns.mean() if len(neg_returns) > 0 else 0
    
    return {
        'var_95': round(var_95, 2),
        'cvar_95': round(cvar_95, 2) if not np.isnan(cvar_95) else None,
        'max_daily_loss': round(max_loss, 2),
        'avg_loss_on_neg_days': round(avg_loss, 2) if not np.isnan(avg_loss) else None,
        'risk_level': '高风险' if abs(var_95) > 3 else ('中风险' if abs(var_95) > 2 else '低风险')
    }

# ==================== 研究7: 最大回撤 ====================

def analyze_drawdown(stock_df):
    """
    分析最大回撤
    """
    prices = stock_df['close'].values
    
    # 计算累计最大值
    peak = prices[0]
    max_dd = 0
    max_dd_duration = 0
    
    current_dd_duration = 0
    dd_start = 0
    dd_end = 0
    peak_at_dd_start = prices[0]
    
    for i, price in enumerate(prices):
        if price > peak:
            peak = price
            current_dd_duration = 0
        else:
            current_dd_duration += 1
            dd = (peak - price) / peak * 100
            
            if dd > max_dd:
                max_dd = dd
                dd_end = i
                dd_start = i - current_dd_duration + 1
                peak_at_dd_start = prices[dd_start]
    
    # 回撤持续时间
    dd_duration = dd_end - dd_start
    
    # 恢复时间(从回撤低点回升的时间)
    if dd_end < len(prices) - 1:
        recovery = (prices[dd_end] - prices[dd_end+1]) / prices[dd_end] * 100 if dd_end + 1 < len(prices) else 0
    else:
        recovery = 0
    
    return {
        'max_drawdown_pct': round(max_dd, 2),
        'drawdown_duration_days': dd_duration,
        'recovery_trading_days': recovery,
        'risk_assessment': '极大风险' if max_dd > 30 else ('高风险' if max_dd > 20 else ('中风险' if max_dd > 10 else '低风险'))
    }

# ==================== 研究8: 交易成本分析 ====================

def analyze_transaction_costs(trades, commission=0.0003, stamp_tax=0.001, slippage=0.0005):
    """
    计算交易成本影响
    """
    if not trades:
        return None
    
    total_return = 0
    cost_return = 0
    
    for trade in trades:
        profit = trade['profit']
        
        # 买入成本
        buy_cost = commission + slippage
        # 卖出成本
        sell_cost = commission + stamp_tax + slippage
        # 总成本
        total_cost = buy_cost + sell_cost
        
        gross = profit
        net = profit - total_cost * 100  # 转换为百分比
        
        total_return += gross
        cost_return += net
    
    # 成本占比
    cost_ratio = abs(cost_return - total_return) / abs(total_return) * 100 if total_return != 0 else 0
    
    return {
        'gross_return': round(total_return, 2),
        'net_return': round(cost_return, 2),
        'cost_pct': round(cost_ratio, 1),
        'cost_impact': '显著' if cost_ratio > 20 else ('中等' if cost_ratio > 10 else '轻微'),
        'recommendation': '降低交易频率' if cost_ratio > 20 else '正常'
    }

# ==================== 研究9: 多时间框架分析 ====================

def analyze_multi_timeframe(stock_df):
    """
    多时间框架分析
    周线 + 日线共振
    """
    stock_df = stock_df.copy()
    stock_df['MA5'] = stock_df['close'].rolling(5).mean()
    stock_df['MA20'] = stock_df['close'].rolling(20).mean()
    stock_df['MA60'] = stock_df['close'].rolling(60).mean()
    
    # 日线趋势
    daily_trend = 'UP' if stock_df['MA5'].iloc[-1] > stock_df['MA20'].iloc[-1] else 'DOWN'
    
    # 多头排列
    daily_bullish = stock_df['MA5'].iloc[-1] > stock_df['MA20'].iloc[-1] > stock_df['MA60'].iloc[-1]
    daily_bearish = stock_df['MA5'].iloc[-1] < stock_df['MA20'].iloc[-1] < stock_df['MA60'].iloc[-1]
    
    # 成交量趋势
    vol_ma5 = stock_df['volume'].rolling(5).mean().iloc[-1]
    vol_ma20 = stock_df['volume'].rolling(20).mean().iloc[-1]
    vol_trend = 'UP' if vol_ma5 > vol_ma20 else 'DOWN'
    
    # 综合信号
    if daily_bullish and vol_trend == 'UP':
        signal = '🟢 强烈买入'
        score = 3
    elif daily_trend == 'UP':
        signal = '🟡 谨慎买入'
        score = 2
    elif daily_bearish:
        signal = '🔴 卖出'
        score = 1
    else:
        signal = '⚪ 观望'
        score = 0
    
    return {
        'daily_trend': daily_trend,
        'vol_trend': vol_trend,
        'bullish': daily_bullish,
        'signal': signal,
        'strength_score': score
    }

# ==================== 主程序 ====================

def main():
    print('='*80)
    print('📊 虾米量化系统 - 综合研究引擎')
    print('='*80)
    
    bs.login()
    
    # 获取大盘数据
    print('\\n[1/12] 获取大盘数据...')
    index_df = get_index_data()
    regime_info = analyze_market_regime(index_df)
    print(f'    当前市场状态: {regime_info[\"current_regime\"]}')
    print(f'    状态持续: {regime_info[\"regime_days\"]}天')
    
    # 获取个股数据
    print('\\n[2/12] 获取个股数据...')
    stock_dfs = {}
    for code, name, sector in STOCKS:
        df = get_stock_data(code, START_DATE, END_DATE)
        if df is not None:
            stock_dfs[code] = df
    print(f'    成功获取 {len(stock_dfs)} 只股票数据')
    
    # 存储所有结果
    all_results = {}
    
    # Beta分析
    print('\\n[3/12] Beta分析 (个股与大盘相关性)...')
    beta_results = {}
    for code, name, sector in STOCKS:
        if code in stock_dfs:
            beta = analyze_beta(stock_dfs[code], index_df)
            if beta:
                beta_results[code] = {'name': name, **beta}
    all_results['beta'] = beta_results
    
    # 波动率分析
    print('\\n[4/12] 波动率分析...')
    vol_results = {}
    for code, name, sector in STOCKS:
        if code in stock_dfs:
            vol = analyze_volatility(stock_dfs[code])
            vol_results[code] = {'name': name, **vol}
    all_results['volatility'] = vol_results
    
    # VaR分析
    print('\\n[5/12] VaR尾部风险分析...')
    var_results = {}
    for code, name, sector in STOCKS:
        if code in stock_dfs:
            var = analyze_var(stock_dfs[code])
            if var:
                var_results[code] = {'name': name, **var}
    all_results['var'] = var_results
    
    # 最大回撤分析
    print('\\n[6/12] 最大回撤分析...')
    dd_results = {}
    for code, name, sector in STOCKS:
        if code in stock_dfs:
            dd = analyze_drawdown(stock_dfs[code])
            dd_results[code] = {'name': name, **dd}
    all_results['drawdown'] = dd_results
    
    # 多时间框架分析
    print('\\n[7/12] 多时间框架共振分析...')
    mtf_results = {}
    for code, name, sector in STOCKS:
        if code in stock_dfs:
            mtf = analyze_multi_timeframe(stock_dfs[code])
            mtf_results[code] = {'name': name, **mtf}
    all_results['multi_timeframe'] = mtf_results
    
    # 相关性分析
    print('\\n[8/12] 相关性风险分析...')
    corr_results = analyze_correlations(stock_dfs)
    all_results['correlation'] = corr_results
    
    # 凯利公式仓位
    print('\\n[9/12] 凯利公式仓位计算...')
    kelly_results = {}
    # 从回测数据计算胜率
    for code, name, sector in STOCKS:
        if code in stock_dfs:
            df = stock_dfs[code]
            # 简化计算：使用最近的信号
            wins = (df['pctChg'] > 0).sum()
            losses = (df['pctChg'] < 0).sum()
            total = wins + losses
            win_rate = wins / total if total > 0 else 0.5
            avg_win = df[df['pctChg'] > 0]['pctChg'].mean() if wins > 0 else 1
            avg_loss = abs(df[df['pctChg'] < 0]['pctChg'].mean()) if losses > 0 else 1
            
            kelly = calculate_kelly_position(win_rate, avg_win, avg_loss)
            kelly_results[code] = {'name': name, **kelly}
    all_results['kelly'] = kelly_results
    
    bs.logout()
    
    # ==================== 汇总输出 ====================
    
    print('\\n' + '='*80)
    print('📊 研究结果汇总')
    print('='*80)
    
    # 1. 市场状态
    print(f'''
\\n【1. 市场状态】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前状态: {regime_info['current_regime']}
状态持续: {regime_info['regime_days']}天
牛市天数: {regime_info['bull_days']}天
熊市天数: {regime_info['bear_days']}天
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    
    # 2. Beta排名
    print(f'''
\\n【2. Beta分析 - 个股与大盘相关性】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'名称':<10} {'Beta':<8} {'相关':<8} {'解读':<10}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    sorted_beta = sorted(beta_results.items(), key=lambda x: -x[1]['beta'])
    for code, data in sorted_beta[:10]:
        print(f'{data[\"name\"]:<10} {data[\"beta\"]:<8.2f} {data[\"correlation\"]:<8.2f} {data[\"interpretation\"]:<10}')
    
    # 3. 波动率
    print(f'''
\\n【3. 波动率分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'名称':<10} {'当前波动':<10} {'平均波动':<10} {'ATR%':<8} {'状态'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    sorted_vol = sorted(vol_results.items(), key=lambda x: -x[1]['vol_ratio'])
    for code, data in sorted_vol[:10]:
        print(f'{data[\"name\"]:<10} {data[\"current_volatility\"]:<10.2f}% {data[\"avg_volatility\"]:<10.2f}% {data[\"atr_pct\"]:<8.2f}% {data[\"status\"]}')
    
    # 4. VaR
    print(f'''
\\n【4. VaR尾部风险】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'名称':<10} {'VaR(95%)':<10} {'CVaR':<10} {'最大单日亏':<12} {'风险等级'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    sorted_var = sorted(var_results.items(), key=lambda x: abs(x[1]['var_95']), reverse=True)
    for code, data in sorted_var[:10]:
        print(f'{data[\"name\"]:<10} {data[\"var_95\"]:>+8.2f}% {str(data[\"cvar_95\"] or \"N/A\"):<10} {data[\"max_daily_loss\"]:>+10.2f}% {data[\"risk_level\"]}')
    
    # 5. 最大回撤
    print(f'''
\\n【5. 最大回撤分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'名称':<10} {'最大回撤':<10} {'持续天数':<10} {'风险评估'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    sorted_dd = sorted(dd_results.items(), key=lambda x: -x[1]['max_drawdown_pct'])
    for code, data in sorted_dd[:10]:
        print(f'{data[\"name\"]:<10} {data[\"max_drawdown_pct\"]:>8.2f}% {data[\"drawdown_duration_days\"]:>8}天 {data[\"risk_assessment\"]}')
    
    # 6. 多时间框架
    print(f'''
\\n【6. 多时间框架信号】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'名称':<10} {'日线趋势':<10} {'量能趋势':<10} {'信号'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    sorted_mtf = sorted(mtf_results.items(), key=lambda x: -x[1]['strength_score'])
    for code, data in sorted_mtf[:10]:
        print(f'{data[\"name\"]:<10} {data[\"daily_trend\"]:<10} {data[\"vol_trend\"]:<10} {data[\"signal\"]}')
    
    # 7. 凯利仓位
    print(f'''
\\n【7. 凯利公式仓位】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'名称':<10} {'Kelly':<10} {'安全仓位':<10} {'最大仓位':<10} {'建议'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
    sorted_kelly = sorted(kelly_results.items(), key=lambda x: -x[1]['safe_kelly_pct'])
    for code, data in sorted_kelly[:10]:
        print(f'{data[\"name\"]:<10} {data[\"kelly_pct\"]:>8.1f}% {data[\"safe_kelly_pct\"]:>8.1f}% {data[\"max_position_pct\"]:>8.1f}% {data[\"recommendation\"]}')
    
    # 8. 高相关股票对
    if corr_results and corr_results['high_corr_pairs']:
        print(f'''
\\n【8. 高相关股票对 (相关性>0.7)】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
注意：这些股票不应同时重仓！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')
        for pair in corr_results['high_corr_pairs'][:5]:
            print(f'  {pair[\"stock1\"]} <-> {pair[\"stock2\"]}: 相关性={pair[\"correlation\"]:.2f}')
    
    # 保存结果
    with open('comprehensive_research_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f'''
\\n【9. 结果已保存】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
文件: comprehensive_research_results.json
股票: {len(STOCKS)}只
数据范围: {START_DATE} 至 {END_DATE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━''')

if __name__ == '__main__':
    main()
