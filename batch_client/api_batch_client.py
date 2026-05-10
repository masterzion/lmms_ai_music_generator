import requests
import json
import os
import time
import argparse
import sys
import random

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

API_URL = f"{config.MIDI_LLM_API_BASE}/generate"

def send_to_api(prompt, topic, genre, output_dir):
    """
    Implements the Plan -> Client -> Generator workflow.
    """
    full_url = f"{config.MIDI_LLM_API_BASE}/generate_full"
    plan_url = f"{config.MIDI_LLM_API_BASE}/generate_from_plan"
    convert_url = f"{config.MIDI_LLM_API_BASE}/convert"
    download_url = f"{config.MIDI_LLM_API_BASE}/download"
    
    print(f"\n--- STEP 1: Requesting Plan from {full_url} ---")
    try:
        # 1. Get the plan from the API
        res = requests.post(full_url, json={"user_prompt": prompt}, timeout=3600)
        res.raise_for_status()
        plan_data = res.json()
        
        if plan_data.get("status") != "success":
            print(f"PLAN ERROR: {plan_data.get('message')}")
            return None
            
        plan = plan_data["plan"]
        print(f"SUCCESS: Plan received for '{plan.get('title')}'")
        
        # 2. Send the plan back to the generator for MIDI creation
        print(f"--- STEP 2: Sending Plan to Generator at {plan_url} ---")
        gen_res = requests.post(plan_url, json={"plan": plan}, timeout=3600)
        gen_res.raise_for_status()
        gen_data = gen_res.json()
        
        if gen_data.get("status") != "success":
            print(f"GENERATION ERROR: {gen_data.get('message')}")
            return None
            
        # 3. Download the generated files
        print(f"--- STEP 3: Downloading and Converting {len(gen_data['files'])} MIDI files ---")
        safe_genre = genre.lower().strip()
        safe_topic = topic.lower().strip()
        target_dir = os.path.join(output_dir, safe_genre, safe_topic)
        os.makedirs(target_dir, exist_ok=True)
        
        downloaded_paths = []
        for file_entry in gen_data["files"]:
            remote_path = file_entry["midi_path"]
            info = file_entry["info"]
            
            # Download MIDI
            dl_res = requests.get(download_url, params={"path": remote_path})
            if dl_res.status_code == 200:
                local_filename = f"{info['section']}_{info['track']}_{int(time.time())}.mid".replace(" ", "_")
                local_path = os.path.join(target_dir, local_filename)
                with open(local_path, "wb") as f:
                    f.write(dl_res.content)
                print(f"  SAVED MIDI: {local_path}")
                
                # STEP 4: Convert to WAV via API
                print(f"  CONVERTING to WAV...")
                conv_res = requests.post(convert_url, json={"midi_path": remote_path})
                if conv_res.status_code == 200:
                    conv_data = conv_res.json()
                    if conv_data.get("status") == "success":
                        remote_wav_path = conv_data["wav_path"]
                        # Download WAV
                        wav_dl_res = requests.get(download_url, params={"path": remote_wav_path})
                        if wav_dl_res.status_code == 200:
                            local_wav_path = local_path.replace(".mid", ".wav")
                            with open(local_wav_path, "wb") as f:
                                f.write(wav_dl_res.content)
                            print(f"  SAVED WAV:  {local_wav_path}")
                
                downloaded_paths.append(local_path)
        
        return downloaded_paths

    except Exception as e:
        print(f"CONNECTION ERROR: {e}")
    return None

def run_batch_from_file(file_path, filter_genre=None):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    with open(file_path, "r") as f:
        # Load all valid lines
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith("#")]

    # Shuffle the lines for random order
    random.shuffle(lines)
    print(f"--- Loaded {len(lines)} jobs. Shuffling for random order. ---")

    # Create output structure
    base_output = "batch_client/outputs"
    os.makedirs(base_output, exist_ok=True)

    for line in lines:
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
