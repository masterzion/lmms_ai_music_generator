import requests
import json

URL = "http://192.168.2.188:11434/api/generate"
payload = {
    "model": "llama3:8b",
    "prompt": "Say hello",
    "stream": False
}

try:
    print("Sending request to Ollama...")
    response = requests.post(URL, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json().get('response')}")
except Exception as e:
    print(f"Error: {e}")
