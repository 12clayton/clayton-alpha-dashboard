# 多策略研究实验室（本地集成）

功能分支：feature/multi-alpha-lab。2026-11-10 已合入并推送 main，功能提交 a0655e6；线上首页已确认显示新入口。

运行：`python -m streamlit run app.py`，从侧栏进入多策略研究实验室，或直接运行 `python -m streamlit run pages/10_Multi_Alpha_Strategy_Lab.py`。

新增 src/multi_alpha_strategy.py、pages/10_Multi_Alpha_Strategy_Lab.py 和 tests/test_strategy.py；原入口仅增加页面链接。requirements 增加 scipy、statsmodels。原配置、持仓、缓存和秘密文件未修改。

CSV 使用 date,symbol,high,low,close，必须包含 SPY/QQQ/SHV/GDX/GLD，至少 300 个共同交易日，推荐超过 800 日；上传数据应为一致复权价格。无前向补齐。

修复：CSV 结束日期截断、首笔建仓手续费、首日收益的 CAGR/回撤基准，以及失败回测清除旧结果；新增价格有限性和 OHLC 顺序校验。

限制：收盘信号滞后一日收益是简化成交假设，不代表真实可成交价格；成本为示例，不含完整融资和期权盈亏。HMM 拟合失败会显式回退至波动率模型。风险指标在显示区间开始时包含此前策略历史。论文业绩仅供参考；未经真实行情验证，不可作为实证业绩。

自动测试使用固定随机种子的合成数据，不代表真实收益。真实 Yahoo 行情与原站导航回归结果见下文；CSV 上传由实际浏览器自动操作验证，未由人工点击验收。

验证结果：共 8 项测试通过（7 项主测试 + 1 项结果面板测试）；Python 编译与 git diff --check 通过。覆盖合成回测、敞口限制、Copula/HMM 因果性、下一日及首笔费用、页面初始渲染、CSV 模式切换、失败提示、结果指标与日志 CSV 序列化。随后已补充真实行情与原站导航回归，见下文。


## 2026-11-10 验证补充

- Yahoo Finance 复权 OHLC：2016-01-04 至 2026-11-09，2729 个共同交易日。
- 默认参数、HMM、2020 年起统计：1723 日，CAGR 1.1077%，Sharpe 0.1560，最大回撤 -19.1308%，期末模拟净值 107822.72（初始 100000）。HMM 覆盖率 100%。不含期权盈亏；不代表未来收益。
- 原站公开模式 14 个导航页、私有模式 17 个导航页，外部行情/新闻请求失败场景全部渲染通过。使用原有缓存回退；并非所有按钮和实时接口的穷尽验证。
- 回归修复原有 Markdown 页面 1m/3m 参数不兼容问题。
- 10 项自动测试通过，包括 CSV 上传控件、结束日期截断、无效文件提示与日志导出。
- 真实数据检查发现复权 OHLC 浮点误差，校验采用相对 1e-8 容差，仍拒绝明显错误价格。
- 原始行情、回测日志和验证文件保存在 D:/Codex/outputs/multi-alpha-validation，未加入仓库。

实际浏览器上传真实行情 CSV、回测与日志下载通过；1723 行导出与独立回测完全一致。线上地址：https://clayton-alpha-dashboard-e6u6sihxyh5unouxvpnpmu.streamlit.app/ 。

线上浏览器验收通过：进入实验室、上传真实行情、执行 HMM 回测、查看收益/风险面板、下载日志；线上导出与独立回测在数值容差内逐列一致。页面地址：https://clayton-alpha-dashboard-e6u6sihxyh5unouxvpnpmu.streamlit.app/Multi_Alpha_Strategy_Lab 。
