import keyring

keyring.set_password("mintel", "username", "你的邮箱")
keyring.set_password("mintel", "password", "你的密码")
keyring.set_password("deepseek", "api_key", "你的DeepSeek API Key")
keyring.set_password("deepseek", "model", "deepseek-chat")
