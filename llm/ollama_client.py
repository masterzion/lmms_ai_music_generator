import requests
import config

OLLAMA_URL = f"{config.OLLAMA_API_BASE}/api/generate"

MODEL = "llama3:8b"


def ask_llm(prompt, temperature=0.1):

    response = requests.post(

        OLLAMA_URL,

        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

    )

    data = response.json()
    print(f"Ollama API response: {data}", flush=True)

    return data.get("response", "")
