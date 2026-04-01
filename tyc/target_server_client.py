import json
import requests
import logging

# 配置日志
logger = logging.getLogger(__name__)

# target_server 地址
TARGET_SERVER_URL = "http://localhost:8002/api/target_server"

def send_to_target_server(json_data):
    """
    发送 POST 请求给 target_server
    
    Args:
        json_data: 要发送的 JSON 数据
    """
    try:
        logger.info("[target_server_client] 开始发送数据到 target_server")
        
        # 发送 POST 请求
        response = requests.post(
            TARGET_SERVER_URL,
            json=json_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # 检查响应状态
        if response.status_code == 200:
            logger.info("[target_server_client] 数据发送成功")
        else:
            logger.warning(f"[target_server_client] 数据发送失败，状态码: {response.status_code}")
            logger.warning(f"[target_server_client] 响应内容: {response.text}")
            
    except Exception as e:
        logger.error(f"[target_server_client] 发送数据时发生异常: {e}")

def send_json_file(file_path):
    """
    从文件中读取 JSON 数据并发送给 target_server
    
    Args:
        file_path: JSON 文件路径
    """
    try:
        # 读取 JSON 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 发送数据
        send_to_target_server(json_data)
        
    except Exception as e:
        logger.error(f"[target_server_client] 读取或发送 JSON 文件时发生异常: {e}")
