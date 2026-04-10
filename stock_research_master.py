#!/usr/bin/env python3
"""
股票多智能体研究系统 - 主程序
并行运行5个专业智能体 + 专家团决策

用法:
python3 stock_research_master.py <股票代码> [股票名称]
python3 stock_research_master.py 600519 贵州茅台
python3 stock_research_master.py 000001 平安银行 AI
"""

import sys
import os
import json
import subprocess
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 智能体脚本路径
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__)) + "/agents"
REPORTS_DIR = os.path.dirname(os.path.abspath(__file__)) + "/reports"

# 股票代码到行业的映射
SECTOR_MAP = {
    "600519": "白酒",
    "000001": "银行",
    "300750": "新能源汽车电池",
    "002594": "新能源汽车",
    "600036": "银行",
    "601318": "保险",
    "000858": "白酒",
    "600887": "食品饮料",
    "300015": "医疗服务",
    "688041": "半导体",
    "300760": "医疗器械",
}

def get_sector(code):
    """获取股票所属行业"""
    return SECTOR_MAP.get(code, "其他")

def run_agent(agent_script, code, name, sector=None):
    """运行单个智能体，返回结果"""
    try:
        cmd = [sys.executable, agent_script, code, name]
        if sector:
            cmd.append(sector)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        else:
            return {"error": f"Agent failed: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"error": "Agent timeout"}
    except Exception as e:
        return {"error": str(e)}

def generate_report(code, name):
    """生成完整研究报告"""
    
    print(f"\n{'='*60}")
    print(f"  股票多智能体研究系统")
    print(f"  {name} ({code})")
    print(f"{'='*60}\n")
    
    sector = get_sector(code)
    print(f"📂 行业分类: {sector}")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\n🚀 启动5个专业智能体...\n")
    
    # 准备各智能体路径
    agents = {
        "技术面专家": f"{AGENTS_DIR}/01_technical_agent.py",
        "基本面专家": f"{AGENTS_DIR}/02_fundamental_agent.py",
        "情绪专家": f"{AGENTS_DIR}/03_sentiment_agent.py",
        "国际专家": f"{AGENTS_DIR}/04_international_agent.py",
        "回归测试专家": f"{AGENTS_DIR}/05_backtest_agent.py",
    }
    
    # 并行运行所有智能体
    results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(run_agent, script, code, name, sector): name_key
            for name_key, script in agents.items()
        }
        
        for future in as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result()
                results[agent_name] = result
                status = "✅" if "error" not in result else "❌"
                print(f"  {status} {agent_name} 完成")
            except Exception as e:
                results[agent_name] = {"error": str(e)}
                print(f"  ❌ {agent_name} 失败: {e}")
    
    print(f"\n✅ 所有智能体分析完成！")
    print(f"\n{'='*60}")
    print(f"  专家团决策中...")
    print(f"{'='*60}\n")
    
    # 专家团决策
    try:
        sys.path.insert(0, AGENTS_DIR)
        from expert_panel import expert_panel_decision
        
        expert_result = expert_panel_decision(
            results.get("技术面专家", {}),
            results.get("基本面专家", {}),
            results.get("情绪专家", {}),
            results.get("国际专家", {}),
            results.get("回归测试专家", {})
        )
    except Exception as e:
        expert_result = {"error": f"专家团决策失败: {e}"}
    
    # 生成最终报告
    report = {
        "report_id": f"{code}_{datetime.now().strftime('%Y%m%d%H%M')}",
        "stock_info": {
            "code": code,
            "name": name,
            "sector": sector
        },
        "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "agents_results": results,
        "expert_panel": expert_result
    }
    
    # 保存报告
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file = f"{REPORTS_DIR}/{code}_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report, results, expert_result

def print_summary(report, results, expert_result):
    """打印分析摘要"""
    
    name = report["stock_info"]["name"]
    code = report["stock_info"]["code"]
    
    print(f"\n{'='*60}")
    print(f"📊 《{name} ({code})》多智能体研究报告")
    print(f"{'='*60}\n")
    
    # 各专家意见
    print("【各维度专家意见】\n")
    
    if "技术面专家" in results and "error" not in results["技术面专家"]:
        t = results["技术面专家"]
        score = t.get("综合评分", {}).get("技术面得分", "N/A")
        signal = t.get("趋势判断", {}).get("信号", "N/A")
        print(f"  📈 技术面专家: {t.get('技术面结论', '分析中')} (得分: {score}, 信号: {signal})")
    
    if "基本面专家" in results and "error" not in results["基本面专家"]:
        f = results["基本面专家"]
        print(f"  📋 基本面专家: {f.get('基本面结论', '分析中')}")
    
    if "情绪专家" in results and "error" not in results["情绪专家"]:
        s = results["情绪专家"]
        print(f"  💬 情绪专家: {s.get('消息面结论', '分析中')}")
    
    if "国际专家" in results and "error" not in results["国际专家"]:
        i = results["国际专家"]
        print(f"  🌍 国际专家: {i.get('国际面结论', '分析中')}")
    
    if "回归测试专家" in results and "error" not in results["回归测试专家"]:
        b = results["回归测试专家"]
        print(f"  🔬 回归测试: {b.get('回归测试结论', '分析中')}")
    
    # 专家团决策
    print(f"\n{'='*60}")
    print("🦁 专家团决策")
    print(f"{'='*60}\n")
    
    if "error" not in expert_result:
        score = expert_result.get("加权综合得分", "N/A")
        decision = expert_result.get("专家团决策", {}).get("最终建议", "N/A")
        risk = expert_result.get("专家团决策", {}).get("风险等级", "N/A")
        position = expert_result.get("专家团决策", {}).get("建议仓位", "N/A")
        horizon = expert_result.get("专家团决策", {}).get("时间维度", "N/A")
        
        print(f"  综合得分: {score} 分")
        print(f"  决策: {decision}")
        print(f"  风险: {risk}")
        print(f"  建议仓位: {position}")
        print(f"  时间维度: {horizon}\n")
        
        bullish = expert_result.get("多空论证", {}).get("多方论点", [])
        bearish = expert_result.get("多空论证", {}).get("空方论点", [])
        
        if bullish:
            print(f"  ✅ 多方论点:")
            for arg in bullish[:3]:
                print(f"     • {arg}")
        
        if bearish:
            print(f"\n  ⚠️ 空方论点:")
            for arg in bearish[:3]:
                print(f"     • {arg}")
        
        print(f"\n  💡 最终结论: {expert_result.get('最终结论', '')}")
    else:
        print(f"  专家团决策暂时不可用: {expert_result.get('error')}")
    
    print(f"\n{'='*60}")
    print(f"📁 完整报告已保存至: reports/{code}_{datetime.now().strftime('%Y%m%d')}.json")
    print(f"⚠️  免责声明: 本分析仅供参考，不构成投资建议")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 stock_research_master.py <股票代码> [股票名称]")
        print("\n示例:")
        print("  python3 stock_research_master.py 600519 贵州茅台")
        print("  python3 stock_research_master.py 000001 平安银行 AI")
        sys.exit(1)
    
    code = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else code
    
    report, results, expert_result = generate_report(code, name)
    print_summary(report, results, expert_result)
