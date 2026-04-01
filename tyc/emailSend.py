import yagmail

# 登录邮箱（这里也可以用授权码）
yag = yagmail.SMTP(user=os.getenv("EMAIL_USER"), password=os.getenv("EMAIL_PASS"), host=os.getenv("EMAIL_HOST"), port=os.getenv("EMAIL_PORT"))

# 发送邮件
yag.send(
    to="Z1941704428@outlook.com",
    subject="喂",
    contents="爆了"
)

print("邮件发送成功")
