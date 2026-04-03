import os
import yagmail
from loguru import logger


def send_email(subject, contents, to="Z1941704428@outlook.com"):
    """
    发送邮件
    
    Args:
        subject: 邮件主题
        contents: 邮件内容
        to: 收件人邮箱
    
    Returns:
        bool: 是否发送成功
    """
    try:
        # 获取邮箱配置
        email_user = os.getenv("EMAIL_USER")
        email_pass = os.getenv("EMAIL_PASS")
        email_host = os.getenv("EMAIL_HOST", "smtp.office365.com")
        email_port = int(os.getenv("EMAIL_PORT", "587"))
        
        if not email_user or not email_pass:
            logger.error("[emailSend] 邮箱配置不完整，请设置 EMAIL_USER 和 EMAIL_PASS 环境变量")
            return False
        
        # 登录邮箱
        yag = yagmail.SMTP(user=email_user, password=email_pass, host=email_host, port=email_port)
        
        # 发送邮件
        yag.send(
            to=to,
            subject=subject,
            contents=contents
        )
        
        logger.info("[emailSend] 邮件发送成功")
        return True
    except Exception as e:
        logger.error(f"[emailSend] 邮件发送失败: {e}")
        return False
