import requests
import json
import os
import time
import argparse
import sys
import random
import threading
import queue

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Shared queue for plans
plan_queue = queue.Queue()

def fetch_plan(prompt, max_retries=3):
    """
    Step 1: Request the Plan (JSON) from the API with retries.
    """
    full_url = f"{config.MIDI_LLM_API_BASE}/generate_full"
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"  [RETRY {attempt}/{max_retries}] Requesting plan...")
            res = requests.post(full_url, json={"user_prompt": prompt}, timeout=32400)
            res.raise_for_status()
            plan_data = res.json()
            
            if plan_data.get("status") == "success":
                return plan_data["plan"]
            else:
                print(f"  PLAN ERROR (Attempt {attempt}): {plan_data.get('message')}")
        except Exception as e:
            print(f"  PLAN CONNECTION ERROR (Attempt {attempt}): {e}")
        
        if attempt < max_retries:
            time.sleep(10)
    return None

def generate_midi_from_plan(plan, genre, topic, output_dir, max_retries=3, parallel_tracks=-1):
    """
    Step 2 & 3: Send plan to generator, download the SINGLE merged MIDI and WAV.
    """
    plan_url = f"{config.MIDI_LLM_API_BASE}/generate_from_plan"
    convert_url = f"{config.MIDI_LLM_API_BASE}/convert"
    download_url = f"{config.MIDI_LLM_API_BASE}/download"
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"--- [Attempt {attempt}/{max_retries}] Sending Plan to Generator (Parallel: {parallel_tracks}) ---")
            gen_res = requests.post(plan_url, json={
                "plan": plan,
                "parallel_tracks": parallel_tracks
            }, timeout=32400)
            gen_res.raise_for_status()
            gen_data = gen_res.json()
            
            if gen_data.get("status") != "success":
                print(f"  GENERATION ERROR (Attempt {attempt}): {gen_data.get('message')}")
                if attempt < max_retries:
                    time.sleep(10)
                    continue
                return False
                
            remote_midi_path = gen_data["midi_path"]
            print(f"--- Downloading and Converting Merged MIDI ---")
            
            safe_genre = genre.lower().strip()
            safe_topic = topic.lower().strip()
            target_dir = os.path.join(output_dir, safe_genre, safe_topic)
            os.makedirs(target_dir, exist_ok=True)
            
            # 1. Download MIDI
            dl_res = requests.get(download_url, params={"path": remote_midi_path})
            if dl_res.status_code == 200:
                safe_title = plan.get('title', 'song').replace(" ", "_")
                local_filename = f"{safe_title}_{int(time.time())}.mid"
                local_path = os.path.join(target_dir, local_filename)
                with open(local_path, "wb") as f:
                    f.write(dl_res.content)
                print(f"  SAVED MIDI: {local_path}")
                
                # 2. Convert to WAV via API
                print(f"  CONVERTING to WAV...")
                conv_res = requests.post(convert_url, json={"midi_path": remote_midi_path})
                if conv_res.status_code == 200:
                    conv_data = conv_res.json()
                    if conv_data.get("status") == "success":
                        remote_wav_path = conv_data["wav_path"]
                        # 3. Download WAV
                        wav_dl_res = requests.get(download_url, params={"path": remote_wav_path})
                        if wav_dl_res.status_code == 200:
                            local_wav_path = local_path.replace(".mid", ".wav")
                            with open(local_wav_path, "wb") as f:
                                f.write(wav_dl_res.content)
                            print(f"  SAVED WAV:  {local_wav_path}")
            return True
        except Exception as e:
            print(f"  GENERATION CONNECTION ERROR (Attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(10)
    return False

def producer_worker(lines, filter_genre):
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) < 3: continue
        genre, topic, prompt = parts
        genre = genre.strip().replace("<", "").replace(">", "").lower()
        if filter_genre and genre != filter_genre.lower(): continue
            
        while plan_queue.qsize() >= 2:
            print(f"\n[PRODUCER] Buffer full ({plan_queue.qsize()} plans). Waiting...")
            time.sleep(10)
            time.sleep(290) 
            
        print(f"\n[PRODUCER] Requesting Plan for: {topic} [{genre}]")
        plan = fetch_plan(f"<{genre}> {prompt}")
        if plan:
            print(f"\n[PRODUCER] RECEIVED JSON PLAN for '{topic}':")
            print(json.dumps(plan, indent=2))
            plan_queue.put((plan, genre, topic))
            print(f"[PRODUCER] Plan added to queue. Size: {plan_queue.qsize()}")
        time.sleep(2)
    plan_queue.put(None)

def consumer_worker(base_output):
    while True:
        item = plan_queue.get()
        if item is None: break
        plan, genre, topic = item
        print(f"\n[CONSUMER] Processing: {topic} [{genre}]")
        generate_midi_from_plan(plan, genre, topic, base_output)
        plan_queue.task_done()

def run_batch_with_threads(file_path, filter_genre=None):
    if not os.path.exists(file_path): return
    with open(file_path, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.strip().startswith("#")]
    random.shuffle(lines)
    base_output = "batch_client/outputs"
    os.makedirs(base_output, exist_ok=True)
    threading.Thread(target=producer_worker, args=(lines, filter_genre), daemon=True).start()
    cons_thread = threading.Thread(target=consumer_worker, args=(base_output,), daemon=True)
    cons_thread.start()
    cons_thread.join()
    print("\n--- BATCH PROCESS COMPLETE ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default="batch_client/songs_to_generate.txt")
    parser.add_argument("--type", type=str)
    args = parser.parse_args()
    run_batch_with_threads(args.file, filter_genre=args.type)
