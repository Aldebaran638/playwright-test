# folder_patents_hybrid 测试说明

## 运行方式

在项目根目录执行：

```powershell
pytest tests/test_folder_patents_hybrid_task.py -q
```

只跑单个场景：

```powershell
pytest tests/test_folder_patents_hybrid_task.py -k auth_refresh_on_401 -q
```

查看详细输出：

```powershell
pytest tests/test_folder_patents_hybrid_task.py -vv -s
```

## 设计要点

- 所有测试都使用 `tmp_path`，不写入真实业务输出目录。
- 不打开真实浏览器，不访问真实网络。
- 外部依赖通过 monkeypatch + fake 对象替换。
- fake API 使用“剧本驱动”机制，按页码消费动作。
- 关键断言覆盖 page 文件、run_summary、重试与鉴权刷新行为。

## 关键覆盖

- happy path + empty page 停止
- 401 触发鉴权刷新
- transient 错误重试与重试用尽
- resume 跳过已存在页面
- invalid data 结构停止
- total/limit 边界停止
- auth_state 缓存命中/未命中路径
- task 默认参数模式可启动
