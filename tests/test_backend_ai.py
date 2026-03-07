import os
import sys
import requests
import json
from dotenv import load_dotenv

# 确保能导入 services
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_maas_direct():
    print("=== MaaS API Direct Diagnostic ===")
    
    # 负载环境变量
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "HUAWEI_MAAS_API_KEY=" in line:
                    api_key = line.split("=", 1)[1].strip()
                    break
    else:
        print("Error: .env file not found")
        return

    if not api_key:
        print("Error: HUAWEI_MAAS_API_KEY not found in .env")
        return

    print(f"API Key (masked): {api_key[:8]}...{api_key[-4:]}")

    # 这里我们要测试原定的配置
    url = "https://api.modelarts-maas.com/v2/chat/completions"
    model = "deepseek-v3.2" # 原代码里的模型名

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Ping"}],
        "temperature": 0.7,
        "max_tokens": 10
    }

    print(f"Requesting URL: {url}")
    print(f"Using Model: {model}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("Success!")
        elif response.status_code == 404:
            print("Hint: Model not found or Endpoint incorrect. Check model name.")
        elif response.status_code == 401:
            print("Hint: API Key invalid.")
        
    except Exception as e:
        print(f"Network Error: {str(e)}")

if __name__ == "__main__":
    test_maas_direct()
