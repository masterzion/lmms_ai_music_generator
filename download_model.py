from huggingface_hub import snapshot_download
import os

model_id = "slseanwu/MIDI-LLM_Llama-3.2-1B"
local_dir = "models/MIDI-LLM"

print(f"Downloading {model_id} to {local_dir}...")
os.makedirs(local_dir, exist_ok=True)

snapshot_download(
    repo_id=model_id,
    local_dir=local_dir,
    local_dir_use_symlinks=False,
    max_workers=8
)

print("Download complete!")
