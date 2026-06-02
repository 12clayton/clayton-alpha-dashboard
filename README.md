# Global QDII Risk Monitor & Industry Trend Search Engine

## Project Overview

`Global_QDII_Risk_Monitor` 是一个本地运行的投资研究辅助项目。项目最初用于观察 QDII、全球 ETF、黄金、美元、美债和主题资产的风险状态，后续扩展出独立入口 `industry_app.py`，形成 **Industry Trend Search Engine / 行业趋势搜索引擎**。

当前重点展示模块是行业趋势研究系统：用户输入行业关键词，例如半导体、CPO、AI 算力、黄金、房地产、白酒、Memory、Robotics 等，系统会生成行业趋势页面，并提供行业雷达总览、市场价格确认、催化事件框架、轻量新闻观察、综合判断卡和 Markdown / JSON 导出。

项目定位是 **research assistant / 研究辅助工具**，用于结构化观察趋势、价格确认、新闻热度、风险信号和数据质量。它不连接券商账户，不执行交易，也不输出直接交易指令。

## Why I Built This

行业主题研究常见问题是信息分散：价格走势、产业链、热点新闻、风险信号、行业阶段和个人研究记录往往分布在不同工具里。这个项目尝试把这些信息组织成一个本地、可解释、可审计的研究界面。

核心目标：

- 把行业研究拆成清晰模块，而不是只看单一价格涨跌。
- 用公开市场代理数据观察价格层面的趋势确认。
- 用本地催化事件框架保持行业逻辑一致性。
- 用轻量新闻观察提供证据层，但不做 AI 自动结论。
- 通过 audit scripts 检查数据完整性、语言一致性和语义质量。
- 让项目可以作为个人研究系统、产品原型和 GitHub 作品展示。

## Key Features

- **Standalone Industry App**：`industry_app.py` 独立运行，不显示原 dashboard 侧边栏。
- **Single Industry Search**：支持中英文关键词和 alias 匹配，未命中时展示 generic framework。
- **Industry Radar Overview**：横向比较所有行业的框架趋势分、V3 市场价格确认、新闻热度和综合状态。
- **V3 Market Price Confirmation**：使用公开市场代理数据和 yfinance，计算 MA breadth、3M median return、relative strength 和市场价格确认分。
- **V4.1 Catalyst Framework**：全行业本地催化事件框架，包含 heat score、heat level、heat direction 和事件表。
- **V4.2 Live News Watch Lite**：通过 yfinance ticker news 做轻量新闻观察，支持本地缓存、去重、关键词匹配和 relevance 过滤。
- **Overall View Card**：用固定规则生成综合状态、透支风险、关键标签和一句话解释。
- **Industry Radar History**：支持本地雷达快照、watchlist、CSV 下载和历史对比。
- **Export to ChatGPT Context**：单行业页可导出中文/英文 Markdown 与 JSON，便于继续做解释型分析。
- **Audit Scripts**：检查行业字段、catalyst 字段、news provider schema 和 semantic quality。

## System Architecture

核心模块：

```text
industry_app.py
├── src/industry_trend_page.py       # 单行业搜索页
├── src/industry_radar_page.py       # 行业雷达总览
├── src/industry_trend_data.py       # 行业 mock framework 数据
├── src/industry_market_data.py      # V3 市场价格确认
├── src/industry_catalyst_data.py    # V4.1 催化事件框架
├── src/industry_news_provider.py    # V4.2 新闻观察 Lite
├── src/industry_overall_view.py     # 综合判断规则
├── src/industry_export.py           # Markdown / JSON 导出
├── src/industry_radar_history.py    # 本地快照与 watchlist
└── scripts/audit_industry_*.py      # 数据质量和语义审计
```

详细说明见：

- `docs/system_architecture.md`
- `docs/project_overview.md`
- `docs/demo_guide.md`
- `docs/roadmap.md`

## Data Sources

本项目区分三类数据口径：

1. **V1/V2 Mock Framework**
   - 来自本地 `industry_trend_data.py`。
   - 用于行业阶段、趋势状态、驱动因素、产业链、风险信号等基础框架。

2. **V3 Market Price Confirmation**
   - 使用公开市场代理样本，例如 ETF 和代表性公司 ticker。
   - 通过 yfinance 获取价格数据。
   - 计算 MA20 / MA50 / MA200 breadth、1M / 3M / 6M return、median 3M return、relative strength 和市场价格确认分。
   - 如果数据失败或行业尚未配置代理样本，页面会 fallback，不崩溃。

3. **V4.1 / V4.2 News & Catalysts**
   - V4.1 是本地催化事件框架数据，不是实时新闻。
   - V4.2 是轻量真实新闻观察，只负责抓取、缓存、去重、关键词匹配和 relevance 过滤。
   - V4.2 不做 AI 自动总结，不做复杂 NLP，不覆盖 V4.1 框架分数。

## How to Run

安装依赖：

```bash
pip install -r requirements.txt
```

运行独立行业趋势搜索引擎：

```bash
streamlit run industry_app.py
```

运行原 dashboard：

```bash
streamlit run app.py
```

两者是独立入口：

- `industry_app.py`：只展示 Industry Trend Search Engine。
- `app.py`：保留原 Global QDII / Clayton Alpha dashboard。

## How to Use

1. 打开 `industry_app.py`。
2. 在顶部选择语言：中文 / English。
3. 使用 `单行业搜索`：
   - 输入 `半导体`、`CPO`、`Gold`、`白酒`、`Memory` 等关键词。
   - 查看综合判断、趋势摘要、核心评分、市场价格确认摘要和新闻热度摘要。
   - 展开市场价格明细、新闻与催化事件、产业链与风险信号、说明 Guide。
   - 使用导出区生成 Markdown / JSON。
4. 使用 `行业雷达总览`：
   - 查看所有行业核心列。
   - 使用分类、V3 状态、搜索和 watchlist 筛选。
   - 展开图表、历史快照、数据更新与维护、开发者信息。

## Audit & Data Quality Checks

建议在提交或展示前运行：

```bash
python scripts/audit_industry_trend_data.py
python scripts/audit_industry_catalyst_data.py
python scripts/audit_industry_news_provider.py
python scripts/audit_industry_semantic_quality.py
python -m compileall industry_app.py src scripts
```

这些脚本检查：

- 中文字段是否完整。
- 中文模式是否残留明显英文模板。
- alias 是否存在明显歧义。
- catalyst 数据字段和枚举是否完整。
- news provider schema 是否完整。
- 行业字段是否存在明显语义错配或模板污染。

## Current Limitations

- V3 市场价格确认依赖 Yahoo Finance / yfinance，网络和数据稳定性可能受限。
- 部分行业没有高质量公开市场代理样本，系统会明确标记 `no_market_mapping`。
- V4.1 catalyst 是本地框架数据，不代表实时事件数据库。
- V4.2 新闻观察是轻量层，仅做抓取、缓存、去重和关键词过滤。
- 系统不接财报 API，不做研报解析，不做 AI 自动研究结论。
- 新闻标题可能来自英文源，中文界面中仍保留新闻原文。

## Future Roadmap

短期：

- Public Demo Mode
- 导出样式继续打磨
- 行业覆盖质量复查

中期：

- Multi-source News Standardization
- SQLite local database
- Radar snapshot analytics
- Theme Discovery Engine

长期：

- Portfolio-aware sector monitoring
- 多语言数据字典
- 更稳定的数据质量分层
- 可共享的公开研究 demo

## Disclaimer

本项目仅用于研究观察、数据整理和趋势解释辅助。所有评分、状态、标签和导出内容都应被理解为研究框架中的结构化信息，不构成财务、法律或税务意见，也不提供直接交易指令。

公开市场数据和新闻数据可能延迟、缺失或存在来源偏差。历史数据、缓存数据和本地 mock framework 均不代表未来结果。
