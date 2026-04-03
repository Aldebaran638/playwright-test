# risk_2_async

这是 `risk_2` 的独立异步试验版，目标是避免 `playwright.sync_api` 在线程并发时出现的 `greenlet` 线程切换错误。

当前版本特点：

- 使用 `playwright.async_api`
- 保持单一已登录 `BrowserContext`
- 在同一个 context 下创建多个 `Page` worker
- 默认并发数为 2
- 由主流程统一汇总并写入结果文件 `risk_2_async_results.json`

当前目录结构：

- `main.py`：异步主流程与 worker 调度
- `browser_context_async.py`：异步浏览器上下文初始化与 cookies 处理
- `run_step_async.py`：异步步骤包装器
- `login_state_async.py`：异步登录态检测
- `navigate_async.py`：异步导航到风险详情页
- `extract_async.py`：异步提取风险记录
- `paging_async.py`：异步翻页判断与翻页执行
- `run_async.py`：运行入口

建议验证顺序：

1. 先将 `name_list_test.txt` 缩到 2 到 4 家公司。
2. 运行 `python tyc/modules/risk_2_async/run_async.py`。
3. 观察同一 context 下双 page 是否稳定。
4. 确认稳定后再逐步扩大样本量。

注意：

- 这是独立试验版，未替换原 `risk_2`。
- 旧的 `run_step.py`、`risk_2_main.py` 不受影响。
- 如果站点在双 page 下仍然出现状态串扰，需要继续针对页面初始化和限速策略做调优。