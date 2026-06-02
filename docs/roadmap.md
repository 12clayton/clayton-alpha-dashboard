# Roadmap

## Current Stable Version

当前稳定版本聚焦 Industry Trend Search Engine：

- 独立入口 `industry_app.py`
- 单行业搜索
- 行业雷达总览
- V3 市场价格确认
- V4.1 全行业催化事件框架
- V4.2 真实新闻观察 Lite
- V4.9 综合判断卡
- 单界面收敛
- Markdown / JSON 导出
- 新闻相关性过滤
- 雷达页维护信息折叠
- semantic quality audit

当前版本适合作为本地研究工具和作品展示版本。

## Short-term Polish

短期不建议继续大规模加功能，优先打磨展示质量：

- Public Demo Mode：隐藏本地敏感配置和缓存路径。
- 导出 Markdown 样式继续优化。
- README 与 demo 截图补充。
- 行业覆盖质量复查。
- 更细的数据质量 badge。
- 统一中文 / English 文案细节。

## Medium-term Expansion

中期可以在保持边界清晰的前提下扩展：

- Multi-source News Standardization：把新闻源统一成 provider interface。
- SQLite local database：替代零散 JSON / CSV 缓存。
- Radar snapshot analytics：对历史快照做趋势变化统计。
- Industry Coverage Review：周期性检查行业分类和市场代理样本。
- Theme Discovery Engine：从 watchlist、新闻关键词和行业热度中发现主题线索。
- Portfolio-aware sector monitoring：把行业雷达和个人组合暴露做映射。

## Long-term Vision

长期方向是做成一个本地优先、可解释、可审计的研究工作台：

- 支持多资产和多行业统一监控。
- 支持本地知识库和研究笔记联动。
- 支持更多公开数据源，但保持数据质量标记。
- 支持跨行业主题关系图谱。
- 支持团队或公开 demo 的只读展示模式。

## Guardrails

后续迭代仍应遵守：

- 不把系统包装成自动交易工具。
- 不用单一数据源做强结论。
- 不让 mock framework 伪装成实时事实。
- 不让新闻 feed 直接替代研究判断。
- 不输出直接交易指令。
