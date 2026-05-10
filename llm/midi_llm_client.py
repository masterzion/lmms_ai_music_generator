import requests
import pretty_midi
import os
import config

def generate_midi_clip(prompt):
    """
    Calls the local FastAPI server for slseanwu/MIDI-LLM_Llama-3.2-1B generation.
    Returns a pretty_midi object containing the generated clip.
    """
    url = f"{config.MIDI_LLM_API_BASE}/generate"
    payload = {"prompt": prompt, "temperature": 1.0}
    
    print(f"\n[MIDI-LLM] Requesting clip from {url}...", flush=True)
    print(f"[MIDI-LLM] Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"[MIDI-LLM] Prompt: {prompt}", flush=True)
    
    try:
        response = requests.post(url, json=payload, timeout=1300)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") == "success":
            remote_midi_path = data.get("midi_path")
            
            # 1. Download the file from the remote server
            download_url = f"{config.MIDI_LLM_API_BASE}/download"
            print(f"[MIDI-LLM] Success! Downloading MIDI: {remote_midi_path}", flush=True)
            
            file_response = requests.get(download_url, params={"path": remote_midi_path})
            file_response.raise_for_status()
            
            # 2. Save it to a local temporary directory
            local_temp_dir = "outputs/api_generated"
            os.makedirs(local_temp_dir, exist_ok=True)
            local_path = os.path.join(local_temp_dir, os.path.basename(remote_midi_path))
            
            with open(local_path, "wb") as f:
                f.write(file_response.content)
            
            print(f"[MIDI-LLM] Saved locally to: {local_path}", flush=True)
            
            # Load the downloaded MIDI
            midi = pretty_midi.PrettyMIDI(local_path)
            return midi
        else:
            raise Exception(data.get("message", "Unknown API error"))
            
    except Exception as e:
        print(f"[MIDI-LLM] FAILED: {e}", flush=True)
        return None
