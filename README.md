# Global_QDII_Risk_Monitor

Global_QDII_Risk_Monitor 是一个 Python 投资研究项目，用于观察全球资产、QDII 基金、黄金、美元、美债、半导体、CPO、AI 算力、比特币等资产的价格趋势和风险状态。

项目只输出研究观察和风险提示，不包含自动交易、下单或择时指令。

## 项目结构

```text
Global_QDII_Risk_Monitor/
├── config/
│   ├── assets.yaml          # 资产监控配置
│   ├── app_mode.yaml        # public/private 展示模式配置
│   ├── dca_policy.yaml      # 每日定投和机动资金规则
│   ├── news_keywords.yaml   # 新闻关键词分组
│   ├── news_sources.yaml    # 新闻源配置
│   ├── portfolio.yaml       # 当前基金组合配置
│   ├── qdii_premium.csv     # QDII 溢价观察数据
│   └── user_profile.yaml    # Clayton Alpha Dashboard 个性化配置
├── backups/                 # 手动保存配置前的自动备份
├── data/                    # 本地价格数据缓存
├── logs/                    # 每日更新日志
├── notebooks/               # 研究笔记本
├── reports/                 # 每日 Markdown 报告
├── src/
│   ├── data_fetcher.py      # 获取价格数据
│   ├── dca_decision_engine.py # 每日定投决策辅助
│   ├── indicators.py        # 计算均线、RSI、最大回撤
│   ├── news_digest.py       # 每日投资资讯摘要
│   ├── report_generator.py  # 生成 Markdown 报告
│   └── risk_model.py        # 判断 risk-on / neutral / risk-off
├── main.py                  # 一键运行入口
├── app.py                   # 最新日报可视化网站
├── run_daily_update.bat     # Windows 每日更新脚本
├── streamlit_app.py         # 本地投资仪表盘
└── requirements.txt         # Python 依赖
```

## 安装依赖

建议使用 Python 3.10 或更高版本。

```bash
pip install -r requirements.txt
```

## 运行方法

生成每日 Markdown 报告：

```bash
python main.py
```

运行后，程序会：

1. 读取 `config/assets.yaml` 中配置的资产；
2. 获取每个资产的历史价格；
3. 计算均线、RSI、最大回撤等指标；
4. 判断每个资产的风险状态；
5. 生成每日定投辅助和机动资金观察；
6. 抓取并生成每日投资资讯摘要；
7. 在 `reports/` 文件夹生成每日 Markdown 报告。

新闻模块会额外生成：

- `reports/news_digest_YYYY-MM-DD.md`
- `reports/news_digest_YYYY-MM-DD.csv`
- `logs/news_digest_YYYY-MM-DD.log`

启动本地 Streamlit 仪表盘：

```bash
streamlit run app.py
```

当前网站名称为 **Clayton Alpha Dashboard**，使用深色金融终端风格，并从 `config/user_profile.yaml` 读取用户名称、今日状态、纪律提醒、主线方向、机动资金参数和版本号。

仪表盘包含：

- 首页 / 今日驾驶舱；
- 每日定投决策；
- 持仓校准；
- 机动资金管理；
- 市场图表与阶段收益；
- 新闻与主题观察；
- 策略回测 / 模型研究；
- 执行复盘记录；
- 当前持仓结构；
- 主题暴露分析；
- 黄金仓位进度；
- 回撤风险仪表盘；
- 手动新闻解析。

首页第一屏会展示今日最终动作、今日模式、基础定投金额、基金分配、黄金动作、灵活资金动作和纪律说明。所有页面均只用于研究观察、风险提示和定投辅助。

“市场图表与阶段收益”页面展示 QQQ、SMH、SOXX、GLD、GC=F、SPY、UUP、TLT 的阶段收益率、归一化收益走势、相对强弱、20/60 日均线、RSI、回撤和技术状态，只用于辅助观察，不生成买入金额。

首页“黄金防守监控”会显示 GC=F、GLD、UUP、TLT、DFII10 等黄金相关指标，用于辅助两周黄金补仓判断，不影响半导体/CPO/CPU 主攻框架或 final_decision。

`config/app_mode.yaml` 可切换 `private` / `public` 模式。`private` 模式显示完整本地持仓、机动资金和编辑功能；`public` 模式会隐藏真实金额、禁用保存和重新生成报告按钮，并隐藏持仓校准、机动资金管理等敏感页面。

## 数据说明

默认使用 Yahoo Finance 数据源，适合做研究观察。不同市场的基金、ETF、指数、商品、外汇或加密资产可能存在交易时区、节假日和数据延迟差异。

如果线上数据获取失败，程序会尝试读取 `data/price_cache.csv` 中的本地缓存，并在报告里提示数据质量。

`config/qdii_premium.csv` 目前使用可手动维护的示例数据，后续可替换为交易所行情、基金估值或第三方 API。

## 风险状态含义

- `risk-on`：价格结构偏强，风险偏好较高；
- `neutral`：信号混合，适合继续观察；
- `risk-off`：价格结构偏弱或回撤压力较大，需要提高警惕。

所有结论仅用于投资研究和风险观察，不构成投资建议。

## 定投辅助说明

系统会根据 `config/portfolio.yaml` 和 `config/dca_policy.yaml` 生成 normal、attack、opportunity、defense 四种观察模式。

定投辅助只用于人工复盘，不会自动交易，不连接券商账户，也不会给出强制买入或卖出指令。

## 每日自动更新

Windows 下可以运行：

```bat
run_daily_update.bat
```

脚本会进入项目目录，运行 `python main.py`，生成每日风险报告和新闻摘要，并将日志保存到 `logs/daily_update_YYYY-MM-DD.log`。

新闻摘要只作为研究辅助，可能存在延迟、误报或来源偏差。

## 新闻解析

`src/news_digest.py` 会读取 `config/news_sources.yaml` 和 `config/news_keywords.yaml`，抓取最近 24 小时新闻，按主题匹配、去重、评分、摘要，并判断对持仓、定投节奏和机动资金的影响。

Streamlit 的“手动新闻解析”页面支持粘贴新闻链接、标题或正文。解析结果可以保存到 `reports/manual_news_notes_YYYY-MM-DD.md`。该功能不自动交易，不连接券商账户，也不会给出强制买卖指令。

## 网页配置编辑

Streamlit 网站内的“持仓校准”和“机动资金管理”页面可以编辑本地 YAML 配置。保存前会自动备份旧文件到 `backups/`，保存后会尝试重新运行 `python main.py` 生成新报告。

这些页面不会连接券商账户，不保存账号密码，不自动交易，也不会自动下单。
