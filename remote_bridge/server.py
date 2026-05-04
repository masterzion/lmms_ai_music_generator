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
    genre: str = "Electronic"
    energy: float = 0.8
    root_midi: int = 60
    intervals: List[int]

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
    # Use inference mode to save VRAM
    with torch.inference_mode():
        try:
            print(f"ACE-Step: Recording '{request.prompt}' ({request.genre}) | Root: {request.root_midi}")
            steps = request.length
            pattern = [-1] * steps
            
            # Determine density based on energy and instrument type
            is_drum = any(k in request.prompt.lower() for k in ["drum", "kick", "perc", "snare", "hat", "clap"])
            density = request.energy if not is_drum else min(0.95, request.energy + 0.1)
            
            # --- MELODIC INTELLIGENCE (Pattern-Based) ---
            motif_len = 4 if is_drum else 8
            motif = []
            
            # Generate a distinct 'Hook' or 'Motif'
            for _ in range(motif_len):
                if np.random.random() < 0.6: # 60% chance of a note
                    if is_drum:
                        motif.append(0)
                    else:
                        interval = np.random.choice(request.intervals)
                        motif.append(interval)
                else:
                    motif.append(-1) # Rest
            
            # Tile and Humanize the motif across the full track length
            for i in range(steps):
                m_idx = i % motif_len
                if motif[m_idx] != -1:
                    # 90% chance to play the motif note, creating 'Musical Variation'
                    if np.random.random() < 0.9:
                        if is_drum:
                            pattern[i] = 0
                        else:
                            # Occasional octave jump for interest
                            octave = np.random.choice([0, 12], p=[0.9, 0.1])
                            pattern[i] = motif[m_idx] + octave
                else:
                    # 10% chance to 'fill' a rest for variety
                    if np.random.random() < 0.1 and not is_drum:
                        pattern[i] = np.random.choice(request.intervals)
            
            # --- PROFESSIONAL ARRANGEMENT LOGIC ---
            all_sections = [0, 1, 2, 3, 4, 5, 6, 7]
            if is_drum or "bass" in request.prompt.lower():
                # Foundation tracks play almost everywhere
                schedule = all_sections
            elif "lead" in request.prompt.lower() or "hook" in request.prompt.lower():
                # Leads play in peak energy sections
                schedule = [2, 3, 5, 6]
            else:
                # Decorative tracks play in alternating sections
                schedule = [i for i in all_sections if i % 2 == 1]
            
            if not schedule: schedule = [0, 1, 2] # Fallback
            
            print(f"ACE-Step: Pattern Success. Schedule: {schedule}")
            
            # Convert to MIDI
            midi_path = "ace_step_output.mid"
            create_midi(pattern, midi_path)
            
            optimize_vram()
            
            return FileResponse(
                path=midi_path, 
                filename="pattern.mid", 
                media_type="audio/midi",
                headers={"X-Schedule": ",".join(map(str, schedule))}
            )
        except Exception as e:
            optimize_vram()
            raise HTTPException(status_code=500, detail=str(e))

class ResearchRequest(BaseModel):
    prompt: str
    system_prompt: str

@app.post("/research_theory")
async def research_theory(request: ResearchRequest):
    """Secondary Director: Suggests theory based on concept."""
    print(f"ACE-Step: Researching theory for '{request.prompt}'...")
    import random
    
    is_chill = any(k in request.prompt.lower() for k in ["chill", "ambient", "relax"])
    is_fast = any(k in request.prompt.lower() for k in ["ebm", "techno", "fast", "dance"])
    
    bpm = random.randint(80, 100) if is_chill else (random.randint(128, 145) if is_fast else 120)
    
    scales = {
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "major": [0, 2, 4, 5, 7, 9, 11]
    }
    scale_name = random.choice(list(scales.keys()))
    
    theory = {
        "bpm": bpm,
        "scale": scale_name,
        "intervals": scales[scale_name],
        "root_midi": random.choice([36, 48, 60]),
        "genre_notes": f"ACE-Step optimized {scale_name} foundation.",
        "title": f"Bridge_Production_{random.randint(1000, 9999)}",
        "folder": "bridge_output"
    }
    
    print(f"ACE-Step: Theory decided. {bpm} BPM, {scale_name}")
    return theory


if __name__ == "__main__":
    load_model()
    uvicorn.run(app, host="0.0.0.0", port=8000)
