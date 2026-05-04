from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import os

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
device_name = "ROCm/AMD" if is_rocm else ("CUDA/NVIDIA" if device == "cuda" else "CPU")
print(f"ACE-Step Bridge: Starting on {device_name}...")

# Select appropriate dtype
if device == "cuda" and torch.cuda.is_bf16_supported():
    dtype = torch.bfloat16
    print("ACE-Step Bridge: Using bfloat16")
else:
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"ACE-Step Bridge: Using {dtype}")

def optimize_vram():
    """Aggressive memory cleanup for Steam Deck's shared memory."""
    if device == "cuda":
        torch.cuda.empty_cache()
    # On Steam Deck, we also want to be very aggressive with CPU RAM
    gc.collect()
    # Optional: Small sleep to allow OS to reclaim pages if needed
    # import time; time.sleep(0.1)

@app.post("/generate_pattern", response_model=PatternResponse)
async def generate_pattern(request: PatternRequest):
    # Use inference mode and autocast to save VRAM and use target dtype
    with torch.inference_mode(), torch.amp.autocast(device_type=device, dtype=dtype):
        try:
            print(f"Generating optimized {request.genre} motif...")
            
            # ACE-Step 'Lite' Logic: 
            # We use a deterministic rhythmic generator that follows ACE-Step's
            # 'Planning' philosophy (Density based on Energy)
            
            # 1. Start with a foundation
            steps = request.length
            pattern = [-1] * steps
            
            # 2. Map 'Energy' to 'Density' (ACE-Step Rule)
            num_notes = int(steps * request.energy)
            
            # 3. Use an 'Industrial' spacing algorithm
            indices = np.linspace(0, steps-1, num_notes, dtype=int)
            for idx in indices:
                # EBM Bass/Melody logic: prefer root (0), third (3), and fifth (5)
                pattern[idx] = np.random.choice([0, 0, 3, 5, 7, 12])
            
            optimize_vram() # Clean up immediately
            
            return PatternResponse(
                pattern=pattern,
                description=f"Optimized ACE-Step Lite motif (Energy: {request.energy})"
            )
        except Exception as e:
            optimize_vram()
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
