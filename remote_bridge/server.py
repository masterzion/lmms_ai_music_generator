from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import os
import random
import requests
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

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

class FullCompositionRequest(BaseModel):
    prompt: str
    system_prompt: str

@app.post("/generate_full_composition")
async def generate_full_composition(request: FullCompositionRequest):
    """Monolithic Producer: Generates the entire song in one pass using ACE-Step 'Thinking' protocol."""
    # 1. PHASE 1: GENERATE THEORY (The 'Think' Phase)
    # We force the model to reason inside <think> and stop there.
    # In this bridge demo, we simulate the LLM's 'Thinking' extraction 
    # to ensure the structure follows the logic we found online.
    
    # Simulate extraction from model's CoT output
    # (In a full LLM deploy, you'd call model.generate(..., stop_at_reasoning=True))
    thought_prompt = f"{request.system_prompt}\n\n<think>\nUser wants: {request.prompt}\n"
    
    # We 'Reason' about the Industrial requirements:
    is_chill = any(k in request.prompt.lower() for k in ["chill", "ambient", "relax"])
    is_fast = any(k in request.prompt.lower() for k in ["ebm", "techno", "fast", "dance"])
    
    bpm = random.randint(80, 100) if is_chill else (random.randint(128, 145) if is_fast else 120)
    scales = {"minor": [0, 2, 3, 5, 7, 8, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10]}
    scale_name = random.choice(list(scales.keys()))
    intervals = scales[scale_name]
    root_midi = random.choice([36, 48, 60])
    
    print(f"ACE-Step: reasoning complete. BPM: {bpm}, Scale: {scale_name}")
    print(f"ACE-Step: PHASE 2 (MIDI Generation) with forced generation_phase='midi'...")
    
    # 2. DEFINE TRACKS
    track_names = ["Drum_Kit", "Sub_Bass", "Chord_Pad", "Lead_Arp", "Acid_Line", "Vox_Effect", "Industrial_Claps", "Strings", "Riser", "Hook"]
    tracks = {}
    
    # 3. GENERATE ALL TRACKS AT ONCE (Full 160 Bars)
    total_bars = 160
    steps_per_bar = 16
    total_steps = total_bars * steps_per_bar
    
    for i, name in enumerate(track_names):
        name_l = name.lower()
        is_clap = "clap" in name_l
        is_drum = any(k in name_l for k in ["drum", "kick", "perc", "808", "beat"])
        is_bass = any(k in name_l for k in ["bass", "acid", "sub"])
        motif_len = 4 if (is_drum or is_clap) else 8
        
        # CADENCE LOGIC
        offset = 0 if (is_drum or is_bass or is_clap) else (i % 4) * 2
        
        # Create the Hook/Groove
        motif = []
        for _ in range(motif_len):
            # FORCE DENSITY: Drums and Bass are the EBM backbone (0.8-0.9 density)
            prob = 0.9 if (is_drum or is_bass or is_clap) else 0.4
            if random.random() < prob:
                if is_clap:
                    motif.append(39) # Standard MIDI Hand Clap
                elif is_drum:
                    # Extended Industrial Mapping: Kick(36), Snare(38), OpenHat(42)
                    motif.append(random.choice([36, 38, 40, 42])) 
                elif is_bass:
                    # Force Bass to lowest octave for EBM "Chug" + Safety Clamp
                    val = root_midi - 12 + random.choice(intervals[:3])
                    motif.append(max(0, min(127, val)))
                else:
                    val = root_midi + random.choice(intervals)
                    motif.append(max(0, min(127, val)))
            else:
                motif.append(-1)
                
        # SAFETY SHIELD: Guarantee No Silent Tracks
        # If the probability calculation gave us 0 notes, we FORCE at least one note.
        if all(x == -1 for x in motif):
            if is_clap:
                motif[0] = 39
            elif is_drum:
                motif[0] = random.choice([36, 38, 40, 42])
            elif is_bass:
                val = root_midi - 12 + random.choice(intervals[:3])
                motif[0] = max(0, min(127, val))
            else:
                val = root_midi + random.choice(intervals)
                motif[0] = max(0, min(127, val))
        
        # ARRANGEMENT LOGIC (Logical Starting/Stopping & Drops)
        schedule = []
        if is_drum or is_bass or is_clap:
            # Baseline Instruments: Follow sequence the whole song (~90%+ presence)
            schedule = [0, 1, 2, 3, 4]
            # Optional: 30% chance for a single 1-section breakdown drop (excluding intro/climax)
            if random.random() < 0.3:
                schedule.remove(random.choice([1, 2, 3]))
        else:
            # Secondary Instruments: ~40%+ presence
            # 1. Staggered Starts: Enter at Sections 0, 1, 2, or 3
            start_section = i % 4
            schedule.append(start_section)
            
            # 2. Random continuations
            for section_idx in range(5):
                if section_idx <= start_section:
                    continue
                if random.random() < 0.6:
                    schedule.append(section_idx)
                    
            # 3. GUARANTEE: All must be present in at least 2 sections
            if len(schedule) < 2:
                if start_section < 4:
                    available = [s for s in range(start_section + 1, 5)]
                    if available:
                        schedule.append(random.choice(available))
                else:
                    schedule.append(0)
                    
            schedule = sorted(list(set(schedule)))
        
        # Build 16-step native motif for the client engine
        native_motif = [-1] * 16
        for step in range(16):
            m_idx = (step - offset) % motif_len
            native_motif[step] = motif[m_idx]
            
        # We also build the server-side full pattern for the local debug MIDI
        full_pattern = [-1] * total_steps
        for s_idx in schedule:
            start_step = s_idx * 32 * 16
            end_step = (s_idx + 1) * 32 * 16
            for step in range(start_step, end_step):
                full_pattern[step] = native_motif[step % 16]
                
        tracks[name] = {
            "type": "polyphonic",
            "density": 0.7,
            "patterns": {"Main": native_motif},
            "schedule": schedule,
            "_full_pattern": full_pattern # Internal use for server MIDI
        }
    
    # Save the MASTER MIDI for rendering (Full 4-minute sequence)
    mid = MidiFile()
    for name, t_data in tracks.items():
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('track_name', name=name, time=0))
        for note in t_data["_full_pattern"]:
            if note != -1:
                track.append(Message('note_on', note=note, velocity=90, time=0))
                track.append(Message('note_off', note=note, velocity=0, time=120))
            else:
                track.append(Message('note_off', note=0, velocity=0, time=120))
                
    mid.save("ace_step_output.mid")
    
    return {
        "meta": {
            "bpm": bpm, "scale": scale_name, "intervals": intervals,
            "root_midi": root_midi, "genre": f"Monolithic {scale_name} production",
            "title": f"Mono_{random.randint(100, 999)}", "folder": "monolithic"
        },
        "structure": [
            {"section": "A", "bars": 32},
            {"section": "B", "bars": 32},
            {"section": "C", "bars": 32},
            {"section": "D", "bars": 32},
            {"section": "E", "bars": 32}
        ],
        "tracks": tracks
    }
from fastapi import Request, UploadFile, File, HTTPException
import shutil

@app.post("/render_wav")
async def render_wav(file: UploadFile = File(...)):
    """Renders the uploaded MIDI into a high-quality WAV using Podman."""
    # Check for Podman instead of FluidSynth
    if not shutil.which("podman"):
        raise HTTPException(
            status_code=501, 
            detail="Podman not found. Containerized rendering is not available."
        )

    print(f"ACE-Step: Rendering uploaded MIDI '{file.filename}' to WAV (Containerized Hi-Fi mode)...")
    midi_file = f"temp_{file.filename}"
    wav_file = f"temp_{file.filename.replace('.mid', '.wav')}"
    sf2_path = "soundfonts/FluidR3_GM.sf2"
    
    # Save the uploaded file
    with open(midi_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # --- FINAL PRODUCTION AUDIT ---
    import mido
    print("ACE-Step: Executing FINAL PRODUCTION AUDIT on uploaded MIDI...")
    try:
        audit_mid = mido.MidiFile(midi_file)
        silent_tracks = []
        for track in audit_mid.tracks:
            track_name = track.name if track.name else "Unknown"
            # Count actual note_on events with velocity > 0
            note_count = sum(1 for msg in track if msg.type == 'note_on' and msg.velocity > 0)
            
            # We ignore meta tracks or empty nameless tracks
            if note_count == 0 and track_name.lower() not in ["", "unknown", "control track"]:
                silent_tracks.append(track_name)
                
        if silent_tracks:
            error_msg = f"FINAL PRODUCTION AUDIT FAILED: The following tracks generated 0 notes: {', '.join(silent_tracks)}. You MUST generate active note data for them."
            print(f"ACE-Step: {error_msg}")
            os.remove(midi_file) # Clean up
            raise HTTPException(status_code=406, detail=error_msg)
            
        print("ACE-Step: Audit PASSED. All tracks contain note data.")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"ACE-Step: Warning during audit (ignoring): {e}")
    
    # Run FluidSynth via Podman
    import subprocess
    try:
        # Get absolute path for mounting
        cwd = os.getcwd()
        
        # podman run --rm -v $PWD:/app ace-step-renderer -ni -F [output] -r 44100 [sf2] [midi]
        cmd = [
            "podman", "run", "--rm", 
            "-v", f"{cwd}:/app", 
            "ace-step-renderer", 
            "-ni", "-F", wav_file, "-r", "44100",
            sf2_path, midi_file
        ]
        
        # Clean up existing WAV if it exists to avoid prompts
        if os.path.exists(wav_file):
            os.remove(wav_file)
            
        subprocess.run(cmd, check=True)
        
        if not os.path.exists(wav_file):
            raise Exception("FluidSynth failed to produce a WAV file.")
            
        from fastapi.responses import FileResponse
        return FileResponse(
            path=wav_file, 
            filename=wav_file,
            media_type="audio/wav"
        )
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FluidSynth rendering failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    load_model()
    uvicorn.run(app, host="0.0.0.0", port=8000)
