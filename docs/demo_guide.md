# Demo Guide

这份指南用于演示 Industry Trend Search Engine 当前稳定版本。

## 1. 启动网站

在项目根目录运行：

```bash
streamlit run industry_app.py
```

打开 Streamlit 提供的本地地址。

## 2. 查看行业雷达

进入 `行业雷达总览`：

- 查看核心列：行业、分类、综合状态、市场价格确认分、新闻热度分、透支风险、V3 状态、实时新闻状态。
- 使用分类筛选、V3 状态筛选、搜索行业和 watchlist 筛选。
- 展开 `高级指标` 查看 MA50、3个月中位数表现、相对强弱等详细指标。
- 展开 `图表` 查看价格确认 Top 10、相对强弱 Top 10、MA50 广度 Top 10、新闻热度 Top 10 和 watchlist 历史。

演示重点：

- 雷达页默认读取本地 `latest_radar.csv` 缓存。
- 不会打开页面就自动全量下载市场数据或新闻。
- 数据更新集中在 `数据更新与维护` expander 里。

## 3. 搜索半导体

进入 `单行业搜索`，输入：

```text
半导体
```

重点展示：

- 识别结果
- 综合判断卡
- 趋势摘要
- 框架评分
- V3 市场价格确认摘要
- V4 新闻热度摘要

讲解口径：

- V1/V2 是本地 framework。
- V3 是公开市场代理价格确认。
- V4.1 是本地 catalyst framework。
- V4.2 是轻量新闻观察。

## 4. 查看综合判断

在半导体页面查看 `综合判断`：

- 综合状态
- 趋势阶段
- 价格确认
- 新闻热度
- 透支风险
- 关键标签
- 一句话解释

说明：

综合判断由固定规则生成，不调用 AI，不输出直接交易指令。

## 5. 展开市场价格明细

展开：

```text
市场价格明细
```

可展示：

- ticker 明细表
- MA20 / MA50 / MA200
- 1M / 3M / 6M return
- 数据计算审计
- failed ticker 与原因

说明：

V3 只反映市场价格层面，不代表完整产业基本面结论。

## 6. 查看新闻与催化事件

展开：

```text
新闻与催化事件
```

可展示：

- V4.1 本地催化事件表
- V4.2 实时新闻观察
- 新闻来源、更新时间、7天新闻数
- 新闻 relevance 和 matched keywords 的过滤效果

说明：

V4.2 是轻量新闻证据层，不做 AI 自动总结。

## 7. 导出 Markdown 给 ChatGPT

展开：

```text
导出分析上下文
```

展示：

- Copy-ready Markdown
- Download Markdown
- Download JSON

建议演示复制 Markdown 到 ChatGPT，让它基于系统上下文做结构化解释。注意：导出内容要求后续分析不要给直接交易指令。

## 8. 运行 Audit

展示命令：

```bash
python scripts/audit_industry_trend_data.py
python scripts/audit_industry_catalyst_data.py
python scripts/audit_industry_news_provider.py
python scripts/audit_industry_semantic_quality.py
python -m compileall industry_app.py src scripts
```

演示重点：

- 中文字段完整性
- 英文残留检查
- alias 歧义检查
- catalyst 字段检查
- news provider schema 检查
- semantic quality 检查

## Demo Narrative

推荐讲法：

> 这个项目不是自动交易工具，而是一个本地行业研究终端。它把行业趋势拆成 framework、market price confirmation、catalyst framework、live news watch 和 overall view 几个层次，再用 audit scripts 保证数据结构和语义质量。核心价值是把混乱的行业主题信息变成可解释、可导出、可复核的研究上下文。
