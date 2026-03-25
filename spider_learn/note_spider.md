```
loguru 是一个优秀的 Python 日志库，它用极简的 API 解决了以上所有问题。

loguru 基本使用
首先安装 loguru：

bash
pip install loguru
最简单的使用方式：

python
from loguru import logger

logger.debug("这是一条调试信息")
logger.info("这是一条普通信息")
logger.warning("这是一条警告信息")
logger.error("这是一条错误信息")
logger.critical("这是一条严重错误信息")
运行后你会看到彩色的、带时间戳和文件位置的日志输出：


2024-03-28 10:30:00.123 | DEBUG    | __main__:<module>:3 - 这是一条调试信息
2024-03-28 10:30:00.124 | INFO     | __main__:<module>:4 - 这是一条普通信息
2024-03-28 10:30:00.125 | WARNING  | __main__:<module>:5 - 这是一条警告信息
2024-03-28 10:30:00.126 | ERROR    | __main__:<module>:6 - 这是一条错误信息
2024-03-28 10:30:00.127 | CRITICAL | __main__:<module>:7 - 这是一条严重错误信息
```


请求伪装
```
User-Agent 轮换：使用真实浏览器 UA，随机轮换避免被追踪
请求头完整伪装：构建与真实浏览器一致的完整请求头
TLS 指纹模拟：使用 curl_cffi 模拟浏览器的 TLS 指纹
速率控制：使用随机延迟和令牌桶算法控制请求频率
HTTP 错误处理：正确处理各种 HTTP 状态码
```

代理IP(防止被封IP)