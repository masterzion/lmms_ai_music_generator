import requests
import json
import time

API_URL = "http://127.0.0.1:9000"

def run_test():
    print("--- STEP 1: Planning Song ---")
    res = requests.post(f"{API_URL}/generate_full", json={"user_prompt": "<ebm> Dark EBM: Aggressive Dissonance"})
    if res.status_code != 200:
        print(f"FAILED Plan: {res.text}")
        return
    
    plan_data = res.json()
    print(f"SUCCESS: Plan received for '{plan_data['plan']['title']}'")

    print("\n--- STEP 2: Generating MIDI with Orpheus ---")
    gen_res = requests.post(f"{API_URL}/generate_from_plan", json={"plan": plan_data['plan']})
    if gen_res.status_code != 200:
        print(f"FAILED Generation: {gen_res.text}")
        return
    
    gen_data = gen_res.json()
    print(f"RESULT: {gen_data}")

if __name__ == "__main__":
    time.sleep(30) # Wait for model load
    run_test()
