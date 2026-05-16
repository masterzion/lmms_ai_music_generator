import requests
import config

OLLAMA_URL = f"{config.OLLAMA_API_BASE}/api/generate"

MODEL = "llama3:8b"


def ask_llm(prompt, temperature=0.1, force_json=False):
    print(f"\n[Ollama] Sending request to {OLLAMA_URL}...", flush=True)
    print(f"[Ollama] Model: {MODEL} | Temperature: {temperature} | JSON Mode: {force_json}", flush=True)
    print(f"[Ollama] Prompt length: {len(prompt)} characters", flush=True)
    print(f"[Ollama] FULL PROMPT:\n{prompt}\n", flush=True)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 4096  # Limit context window to prevent OOM 500 errors
        }
    }
    # if force_json:
    #     payload["format"] = "json"

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=10800
        )
        response.raise_for_status()
    except Exception as e:
        print(f"[Ollama] Request failed: {e}", flush=True)
        return ""

    data = response.json()
    response_text = data.get("response", "")
    print(f"[Ollama] RAW RESPONSE:\n{response_text}\n", flush=True)

    return response_text
