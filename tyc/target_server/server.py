from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# 存储文件路径
STORAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'target_server_data.json')

@app.route('/api/target_server', methods=['POST'])
def receive_data():
    """
    接收 POST 请求并存储数据到 json 文件
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        # 读取现有数据
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        # 添加新数据
        existing_data.append(data)
        
        # 保存到文件
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'status': 'success', 'message': 'Data received and stored'}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)
