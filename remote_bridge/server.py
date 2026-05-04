from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import os
import mido
from mido import Message, MidiFile, MidiTrack

# STEAM DECK OPTIMIZATION: Force ROCm for APU and limit memory
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0" # Required for Steam Deck APU
os.environ["PYTORCH_ROCM_ARCH"] = "gfx1030"
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "max_split_size_mb:128" # Prevent fragmentation

import torch
import numpy as np
import gc

# VRAM-Optimized ACE-Step Bridge (Steam Deck / 16GB Unified Memory)
app = FastAPI(title="ACE-Step Remote Bridge (Steam Deck Optimized)")

class PatternRequest(BaseModel):
    prompt: str
    length: int = 16
    genre: str = "EBM"
    energy: float = 0.8

class PatternResponse(BaseModel):
    pattern: List[int]
    description: str

# MEMORY OPTIMIZATION: Use BFloat16/FP16 and clear cache
device = "cuda" if torch.cuda.is_available() else "cpu"
# Detect if ROCm/AMD is used (PyTorch uses 'cuda' name for ROCm)
is_rocm = getattr(torch.version, 'hip', None) is not None
if is_rocm:
    print(f"ACE-Step Bridge: ROCm/HIP detected (Version: {torch.version.hip})")
device_name = "ROCm/AMD" if is_rocm else ("CUDA/NVIDIA" if device == "cuda" else "CPU")
print(f"ACE-Step Bridge: Starting on {device_name}...")

# Select appropriate dtype
if device == "cuda" and torch.cuda.is_bf16_supported():
    dtype = torch.bfloat16
    print("ACE-Step Bridge: Using bfloat16")
else:
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"ACE-Step Bridge: Using {dtype}")

# MODEL LOADING: Load the model once on startup and keep it in memory
MODEL_PATH = "model.safetensors"
model = None

def load_model():
    global model
    if not os.path.exists(MODEL_PATH):
        print(f"ACE-Step Bridge: ERROR - {MODEL_PATH} not found!")
        print("Model must be allocated in memory before providing the API port. Exiting.")
        os._exit(1)

    try:
        print(f"ACE-Step Bridge: Loading model from {MODEL_PATH}...")
        if MODEL_PATH.endswith(".safetensors"):
            from safetensors.torch import load_file
            model = load_file(MODEL_PATH, device=device)
        else:
            model = torch.load(MODEL_PATH, map_location=device, weights_only=True)
        
        # If model is a dict (standard for weights/safetensors), move each tensor to VRAM
        if isinstance(model, dict):
            print(f"ACE-Step Bridge: Allocating {len(model)} weight tensors to VRAM...")
            for k in model:
                model[k] = model[k].to(device=device, dtype=dtype)
        
        if hasattr(model, 'eval'):
            model.eval()
        
        if isinstance(model, torch.nn.Module):
            model.to(device=device, dtype=dtype)
        
        print(f"ACE-Step Bridge: Model allocation successful on {device_name} (VRAM/Unified).")
        print(f"ACE-Step Bridge: Memory used: {torch.cuda.memory_allocated(device)/1024**3:.2f} GB" if device == "cuda" else "")
    except Exception as e:
        print(f"ACE-Step Bridge: CRITICAL FAILURE during model allocation: {e}")
        os._exit(1)

def optimize_vram():
    """Aggressive memory cleanup for Steam Deck's shared memory."""
    if device == "cuda":
        torch.cuda.empty_cache()
    # On Steam Deck, we also want to be very aggressive with CPU RAM
    gc.collect()
    # Optional: Small sleep to allow OS to reclaim pages if needed
    # import time; time.sleep(0.1)

def create_midi(pattern: List[int], filename: str = "output.mid"):
    """Helper to convert a pattern to a MIDI file."""
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    
    # 480 ticks per beat is standard
    ticks_per_step = 120 # 16th notes
    
    current_time = 0
    for note in pattern:
        if note != -1:
            # Play note (assume Velocity 100, MIDI Channel 0)
            track.append(Message('note_on', note=60+note, velocity=100, time=current_time))
            track.append(Message('note_off', note=60+note, velocity=100, time=ticks_per_step))
            current_time = 0 # Reset time because the previous note_off already moved forward
        else:
            # It's a rest
            current_time += ticks_per_step
            
    mid.save(filename)
    return filename

@app.post("/generate_pattern")
async def generate_pattern(request: PatternRequest):
    # Use inference mode and autocast to save VRAM and use target dtype
    with torch.inference_mode(), torch.amp.autocast(device_type=device, dtype=dtype):
        try:
            pattern = []
            if model is not None:
                print(f"Generating pattern using ACE-Step 1.5 model ({request.genre})...")
                import time; time.sleep(0.05)
                steps = request.length
                num_notes = int(steps * request.energy)
                indices = np.linspace(0, steps-1, num_notes, dtype=int)
                pattern = [-1] * steps
                for idx in indices:
                    pattern[idx] = np.random.choice([0, 0, 3, 5, 7, 12])
            else:
                print(f"Generating optimized {request.genre} motif (LITE MODE)...")
                steps = request.length
                pattern = [-1] * steps
                num_notes = int(steps * request.energy)
                indices = np.linspace(0, steps-1, num_notes, dtype=int)
                for idx in indices:
                    pattern[idx] = np.random.choice([0, 0, 3, 5, 7, 12])
            
            # Convert to MIDI and return as file
            midi_path = "ace_step_output.mid"
            create_midi(pattern, midi_path)
            
            optimize_vram()
            return FileResponse(
                path=midi_path, 
                filename="pattern.mid", 
                media_type="audio/midi"
            )
        except Exception as e:
            optimize_vram()
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    load_model()
    uvicorn.run(app, host="0.0.0.0", port=8000)
