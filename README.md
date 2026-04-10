# 🦐 虾米量化系统

> 专业级A股智能决策系统 - 多智能体协同 · 事件驱动 · 无功能孤岛

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 系统简介

虾米量化系统是一个**专业级A股智能决策系统**，通过多智能体协同工作、事件驱动架构、完整量化因子模型，实现从选股到持仓管理的全流程自动化。

### 核心特性

- 🎯 **多智能体协同** - 18个专业Agent全面协调，无功能孤岛
- ⚡ **事件驱动** - Event Bus总线架构，毫秒级响应
- 📊 **37因子量化模型** - 价格/资金/情绪/政策/基本面/外部/结构/周期
- 🧠 **自适应权重** - 多轮迭代优化，市场状态感知
- 🔄 **完整工作流** - 选股 → 买入 → 监控 → 卖出

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         虾米量化系统架构 v4.0                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Layer 0: Event Bus (事件总线)                    │   │
│  │         所有Agent通过事件总线通信 · 无功能孤岛 · 同步协调            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↑                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Layer 1: 18个专业Agent                         │   │
│  │                                                                      │   │
│  │   技术层  │ 战术层  │ 风控层  │ 情绪层  │ 决策层  │ 执行层          │   │
│  │   ───────│─────────│────────│────────│────────│────────│               │   │
│  │   Technical │ Tactic │ Risk │ News │ Decision │ Execution           │   │
│  │   Sector │ Policy │ Intl │ Money │ Monitor │ ...                    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 18个专业Agent

| Agent | 职责 | 核心能力 |
|:---|:---|:---|
| **TechnicalAgent** | 技术分析 | MA/MACD/RSI/KDJ |
| **TacticAgent** | 战术战法 | 2560战法/突破策略 |
| **RiskAgent** | 风险控制 | VaR/止损/仓位 |
| **NewsAgent** | 新闻事件 | 情绪分析/事件影响 |
| **PositionAgent** | 仓位管理 | 凯利公式/配置优化 |
| **SectorAgent** | 板块轮动 | 资金流向/热点追踪 |
| **PolicyAgent** | 政策监控 | 央行/证监会/国务院 |
| **InternationalAgent** | 国际市场 | 美股/港股/汇率 |
| **MoneyFlowAgent** | 资金流向 | 北向/融资融券 |
| **DecisionAgent** | 决策聚合 | 加权投票/贝叶斯 |

---

## 📊 37因子量化模型

| 类别 | 因子数 | 示例 |
|:---|:---:|:---|
| 价格因子 | 7 | 动量、反转、波动率、Beta、Alpha |
| 资金流 | 4 | 主力净流入、北向资金、融资融券 |
| 情绪因子 | 4 | 新闻情绪、分析师评级、机构调研 |
| 政策因子 | 4 | 货币政策、行业政策、监管政策 |
| 基本面 | 5 | P/E、P/B、ROE、营收增长 |
| 外部冲击 | 5 | 美股、港股、汇率、大宗商品 |
| 市场结构 | 4 | 板块轮动、VIX指数、期现溢价 |
| 时间周期 | 4 | 季节效应、周内效应、财报季 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install numpy pandas tushare baostock akshare
```

### 2. 运行系统

```bash
cd stock-research
python integrated_quantitative_system.py
```

### 3. 运行测试

```bash
python multi_agent_coordination_system.py
```

---

## 📁 目录结构

```
stock-research/
├── multi_agent_coordination_system.py   # 多智能体协调框架
├── integrated_quantitative_system.py    # 完整集成系统
├── comprehensive_quantitative_system.py # 37因子量化模型
├── adaptive_weight_system.py           # 自适应权重优化
├── master_workflow_system.py           # 三大工作流
├── unified_data_source.py              # 统一数据源
├── event_driven_workflow.py           # 事件驱动工作流
├── policy_monitor.py                   # 政策监控
├── international_news_agent.py        # 国际新闻
├── 设计文档_v4.md                     # 设计文档
└── README.md                         # 本文件
```

---

## 📈 核心算法

### 1. 自适应多轮权重优化

```
第1轮: 最大似然估计 (MLE)
第2轮: 贝叶斯更新
第3轮: L2正则化
第4轮: 梯度下降
第5轮: 市场状态调整
→ 收敛检测 → 最优权重
```

### 2. 决策规则

```
buy_votes ≥ 0.6 (60%权重支持) → BUY
avoid_votes ≥ 0.4 (40%权重反对) → AVOID
否则 → HOLD
```

### 3. 风险控制

| 规则 | 参数 |
|:---|:---|
| 最大持仓 | 5只 |
| 单只仓位上限 | 25% |
| 止损位 | -8% |
| 目标位 | +15% |
| 熊市降仓 | 70% |

---

## 📜 事件驱动示例

```
📢 breaking_news (央行降准利好)
    │
    ├─→ NewsAgent → news_analysis
    │       │
    │       ├─→ SectorAgent → sector_change
    │       ├─→ DecisionAgent → final_decision
    │       └─→ PositionAgent → position_calculated
    │
    └─→ PolicyAgent → policy_analysis
```

---

## 📊 版本历史

| 版本 | 日期 | 更新 |
|:---|:---:|:---|
| v1.0 | 04-10 | 12智能体基础架构 |
| v2.0 | 04-10 | ATR/凯利/回测/持仓 |
| v3.0 | 04-11 | 37因子/自适应权重 |
| **v4.0** | 04-11 | **多智能体协调/事件总线** |

---

## 📄 License

MIT License - 欢迎使用和改进

---

**🦐 虾米量化系统 - 让AI为您的投资决策赋能**
