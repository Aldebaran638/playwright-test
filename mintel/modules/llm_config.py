import keyring

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


def get_deepseek_api_key() -> str | None:
    # 从系统凭据管理器中读取 DeepSeek API Key
    return keyring.get_password("deepseek", "api_key")


def get_deepseek_model() -> str:
    # 从系统凭据管理器中读取 DeepSeek 模型名，未配置时回退到默认模型
    return keyring.get_password("deepseek", "model") or DEFAULT_DEEPSEEK_MODEL
