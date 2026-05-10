import requests
import json
import sys
import os

# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def test_ollama():
    print("Testing Ollama (Prompt Expansion)...")
    url = f"{config.OLLAMA_API_BASE}/api/generate"
    payload = {
        "model": "llama3:8b",
        "prompt": "Hello, can you hear me? Answer with one word.",
        "stream": False
    }
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        print(f"Ollama Success: {response.json().get('response', '').strip()}")
    except Exception as e:
        print(f"Ollama Failed: {e}")

def test_midi_llm():
    print("\nTesting MIDI-LLM (Generation)...")
    url = f"{config.MIDI_LLM_API_BASE}/generate"
    # Use a more realistic prompt that the model expects
    payload = {
        "prompt": "PIECE_START <style> chillout </style> <density> 3 </density>",
        "temperature": 1.0
    }
    try:
        print(f"Sending request to {url}... (this might take a moment)")
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        print(f"MIDI-LLM Success: {response.json()}")
    except Exception as e:
        print(f"MIDI-LLM Failed: {e}")

if __name__ == "__main__":
    test_ollama()
    test_midi_llm()
