import os
import sys

# 1. 确保能找到项目里的其他文件夹
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from services.ai_service import ai_service

def test_ai():
    print("Testing AI Service...")
    print(f"API Key found: {bool(ai_service.api_key)}")
    print(f"Model: {ai_service.model}")
    
    try:
        reply = ai_service.chat("你好，请做一个简单的自我介绍。")
        print(f"AI Reply: {reply}")
    except Exception as e:
        print(f"AI Error: {str(e)}")

if __name__ == "__main__":
    test_ai()
