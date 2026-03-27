这是从英敏特上找数据的自动化程序。

根据main中的
```python
TARGET_PRODUCT_NAMES = [
    "Soothing Repair Cream pH 4.5",
    "Hydra + Soft Serve Intense Moisturizing Cream",
    "Night Power Bounce Creme",
]
```

数组,在指定的标签下下载列表中名字的产品word.单线程.内容下载至downloads


## 快速开始
### 1. 安装依赖

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 配置账号（Keyring）
在运行 `main.py` 或 `main2.py` 之前，需要先把账号密码和 DeepSeek 配置写入系统凭据库。
可使用 `info.py`（请先把占位符改成真实信息）：

```python
import keyring

keyring.set_password("mintel", "username", "你的邮箱")
keyring.set_password("mintel", "password", "你的密码")
keyring.set_password("deepseek", "api_key", "你的DeepSeek API Key")
keyring.set_password("deepseek", "model", "deepseek-chat")
```

执行：

```powershell
python info.py
```