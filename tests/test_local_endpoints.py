import requests
import json

def test_local_api():
    print("=== Local API Status Diagnostic ===")
    url = "http://127.0.0.1:8001/api/ai/status"
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error connecting to local backend: {str(e)}")

def test_local_chat():
    print("\n=== Local API Chat Diagnostic ===")
    url = "http://127.0.0.1:8001/api/ai/chat"
    payload = {
        "message": "你好",
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error connecting to local backend: {str(e)}")

if __name__ == "__main__":
    test_local_api()
    # If API status is 200, try a chat
    test_local_chat()
