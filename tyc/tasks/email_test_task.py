from loguru import logger
from tyc.modules.email.emailSend import send_email


def test_email_send():
    """
    测试邮件发送功能
    
    Returns:
        bool: 测试是否成功
    """
    logger.info("[emailTest] 开始测试邮件发送功能")
    
    # 发送测试邮件
    subject = "测试邮件 - 天眼查风险爬虫"
    contents = "这是一封测试邮件，用于验证邮件发送功能是否正常。"
    
    success = send_email(subject, contents)
    
    if success:
        logger.info("[emailTest] 邮件发送测试成功")
    else:
        logger.error("[emailTest] 邮件发送测试失败")
    
    return success


if __name__ == "__main__":
    test_email_send()
