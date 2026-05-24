# Clayton Alpha System Manual

## 系统定位

Global_QDII_Risk_Monitor 是 Clayton 的本地投资研究与定投辅助驾驶舱。

系统用于：

- 监控全球资产风险状态。
- 跟踪 QDII、纳指科技、半导体、CPO、AI算力、黄金、美元、美债和比特币等资产。
- 生成每日风险报告。
- 展示每日定投辅助决策。
- 跟踪新闻、行业主线、组合暴露和黄金防守状态。

系统不用于：

- 自动交易。
- 自动下单。
- 连接券商账户。
- 保存账号密码。
- 给出强制买入或卖出指令。

## 整体架构

核心模块：

- `main.py`：生成每日风险报告和相关数据。
- `app.py`：Streamlit 本地网站入口。
- `config/`：本地配置，包括资产、组合、定投策略、模式和用户画像。
- `src/`：数据获取、指标、风险模型、定投辅助、新闻摘要、黄金防守等逻辑。
- `reports/`：日报、新闻摘要和本地记录。
- `docs/skills/`：系统规则文档，用于约束后续开发。

## Skill 文档作用

### Daily Decision Skill

固定每日动作纪律。

重点：

- `final_decision` 是唯一今日动作来源。
- `do_not_chase` 一票否决。
- 新闻、图表、行业研究不能生成买入金额。
- 黄金不计入每日 `¥60`。

文档位置：

`docs/skills/daily_decision_skill.md`

### News Research Skill

固定新闻解释结构。

重点：

- 每条新闻必须讲清楚发生了什么。
- 必须说明为什么重要、产业链影响、基金映射、观察池和不确定性。
- 新闻不能覆盖 `final_decision`。

文档位置：

`docs/skills/news_research_skill.md`

### Theme Research Skill

固定行业研究框架。

重点：

- thesis。
- 核心驱动。
- 观察指标。
- 产业链地图。
- 股票 / ETF / 基金映射。
- 评分和当前状态。
- 今日动作影响。

文档位置：

`docs/skills/theme_research_skill.md`

### Market Chart Skill

固定市场图表规则。

重点：

- 阶段收益率。
- 归一化收益。
- RSI。
- 回撤。
- 相对强弱。
- K线。
- Plotly key 必须唯一。

文档位置：

`docs/skills/market_chart_skill.md`

### Portfolio X-Ray Skill

固定组合穿透规则。

重点：

- 模块暴露。
- 当前 vs 目标。
- 基金重叠。
- 目标偏离。
- public/private 展示规则。

文档位置：

`docs/skills/portfolio_xray_skill.md`

### Gold Defense Skill

固定黄金防守模块规则。

重点：

- GC=F、GLD、UUP、TLT、DFII10。
- gold_accumulate / gold_wait / gold_hold / gold_pause。
- 黄金两周补仓。
- 黄金不计入每日 `¥60`。

文档位置：

`docs/skills/gold_defense_skill.md`

## 每日使用流程

1. 运行 `python main.py` 生成最新日报和新闻摘要。
2. 打开 Streamlit 网站。
3. 先看“首页 / 今日驾驶舱”。
4. 确认：
   - 今天投多少钱。
   - 投哪些基金。
   - 是否补黄金。
   - 是否动用灵活资金。
   - 为什么这么做。
5. 查看“新闻与主题观察”，理解当天新闻背景。
6. 查看“市场图表与阶段收益”，确认是否过热、回踩或趋势走弱。
7. 如需中长期判断，查看“行业研究 / Clayton Theme Research”。

## 每周校准流程

建议每周至少校准一次：

1. 进入“持仓校准”。
2. 更新真实基金持仓金额。
3. 保存前系统自动备份旧配置。
4. 重新运行 `main.py`。
5. 查看“组合 X-Ray”：
   - 哪些模块低配。
   - 哪些模块高配。
   - 科技 / AI / 半导体是否过度重叠。
6. 查看“黄金仓位进度”和“黄金防守监控”。
7. 确认黄金是否仍低于目标，是否进入下一轮两周补仓。

## public/private 规则

### private 模式

private 模式用于 Clayton 本地使用。

允许：

- 显示真实持仓金额。
- 显示机动资金余额。
- 编辑 portfolio.yaml。
- 编辑 dca_policy.yaml。
- 保存本地配置。
- 显示本地路径。

### public 模式

public 模式用于临时展示。

必须：

- 隐藏真实持仓金额。
- 隐藏机动资金余额。
- 隐藏本地路径。
- 隐藏编辑页面。
- 禁止保存按钮。
- 禁止写入 YAML / CSV。
- 禁止运行 `main.py` 的按钮。

public 模式可以展示：

- 模型结构。
- 市场模式。
- 风险状态。
- 新闻摘要。
- 行业研究。
- 图表和阶段收益。
- 是否追高。
- 是否动用灵活资金的“是/否”状态。

## 不允许改动的核心纪律

后续任何功能都不得破坏以下规则：

1. `final_decision` 是唯一今日动作来源。
2. `do_not_chase` 一票否决。
3. 新闻不能生成买入金额。
4. 行业研究不能生成买入金额。
5. 图表不能生成买入金额。
6. Portfolio X-Ray 不能生成买入金额。
7. 黄金不计入每日 `¥60` 固定定投。
8. 黄金补仓不触发灵活资金。
9. public 模式不得泄露真实金额、本地路径或可编辑入口。
10. 系统不自动交易，不连接券商账户，不保存账号密码。

## 开发检查清单

每次修改后至少检查：

- `python -m py_compile app.py` 是否通过。
- 是否出现多个 Plotly 图表使用同一个 key。
- public 模式是否隐藏金额和路径。
- `do_not_chase` 下是否仍显示 `¥60`、不动用灵活资金、灵活资金 `¥0`。
- 新闻、图表、行业研究是否仍只解释，不生成金额。
- 黄金是否仍作为防守模块单独处理。

