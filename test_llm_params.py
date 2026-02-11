
import requests
import json

MODEL = "qwen3:0.6b"
API_URL = "http://localhost:11434/api/chat"

def test_chat(options=None):
    print(f"Testing with options: {options}")
    messages = [{"role": "user", "content": "Solve 25 * 25"}]
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False
    }
    if options:
        payload["options"] = options

    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status()
        res_json = response.json()
        content = res_json.get("message", {}).get("content", "")
        print(f"Response (first 100 chars): {content[:100]}...")
        if "<think>" in content:
            print("Detected <think> tags in response.")
        else:
            print("No <think> tags detected.")
        return content
    except Exception as e:
        print(f"Error: {e}")
        return None

print("--- Run 1: Default ---")
test_chat()

print("\n--- Run 2: thinking=False ---")
test_chat({"thinking": False}) # "thinking" is a guess based on user request

print("\n--- Run 3: num_think=0 ---") 
test_chat({"num_think": 0}) 
