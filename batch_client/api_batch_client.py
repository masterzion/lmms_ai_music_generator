import requests
import json
import os
import time
import argparse
import sys

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

API_URL = f"{config.MIDI_LLM_API_BASE}/generate"

def send_to_api(prompt, topic, genre, output_dir):
    payload = {
        "prompt": prompt,
        "temperature": 1.0,
        "genre": genre,
        "topic": topic
    }
    
    print(f"--- Sending request for: {topic} ({genre}) ---")
    try:
        response = requests.post(API_URL, json=payload, timeout=1200)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                midi_path = data.get("midi_path")
                print(f"SUCCESS: MIDI generated at {midi_path}")
                return midi_path
            else:
                print(f"API ERROR: {data.get('message')}")
        else:
            print(f"HTTP ERROR: {response.status_code}")
    except Exception as e:
        print(f"CONNECTION ERROR: {e}")
    return None

def run_batch_from_file(file_path, filter_genre=None):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Create output structure
    base_output = "batch_client/outputs"
    os.makedirs(base_output, exist_ok=True)

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"): continue
        
        parts = line.split(":", 2)
        if len(parts) < 3: continue
        
        genre, topic, prompt = parts
        genre = genre.strip().replace("<", "").replace(">", "").lower()
        
        # FILTERING LOGIC
        if filter_genre and genre != filter_genre.lower():
            continue
            
        print(f"\nProcessing Job: {topic} [{genre}]")
        full_prompt = f"<{genre}> {prompt}"
        result = send_to_api(full_prompt, topic, genre, base_output)
        if result:
            time.sleep(2) # Prevent overwhelming the API

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forensic MIDI Batch Client")
    parser.add_argument("--file", type=str, default="batch_client/songs_to_generate.txt", help="Path to jobs file")
    parser.add_argument("--type", type=str, help="Filter by music type (e.g., futurepop, chillout, ebm)")
    
    args = parser.parse_args()
    
    run_batch_from_file(args.file, filter_genre=args.type)
