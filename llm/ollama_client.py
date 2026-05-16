import httpx
import config
import asyncio

OLLAMA_URL = f"{config.OLLAMA_API_BASE}/api/generate"
MODEL = "llama3:8b"

async def ask_llm(prompt, temperature=0.1, force_json=False):
    print(f"\n[Ollama] Sending async request to {OLLAMA_URL}...", flush=True)
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 4096
        }
    }

    try:
        async with httpx.AsyncClient(timeout=1800.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        print(f"[Ollama] Async request failed: {e}", flush=True)
        return ""

# Alias for compatibility with the planner
call_ollama = ask_llm
