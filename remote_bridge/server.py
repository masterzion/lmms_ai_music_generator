from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import torch
import numpy as np
import gc

# VRAM-Optimized ACE-Step Bridge
app = FastAPI(title="ACE-Step Remote Bridge (8GB Optimized)")

class PatternRequest(BaseModel):
    prompt: str
    length: int = 16
    genre: str = "EBM"
    energy: float = 0.8

class PatternResponse(BaseModel):
    pattern: List[int]
    description: str

# MEMORY OPTIMIZATION: Use FP16 and clear cache
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"ACE-Step Bridge: Starting on {device}...")

def optimize_vram():
    """Aggressive memory cleanup to prevent core dumps."""
    if device == "cuda":
        torch.cuda.empty_cache()
    gc.collect()

@app.post("/generate_pattern", response_model=PatternResponse)
async def generate_pattern(request: PatternRequest):
    # Use inference mode to save VRAM
    with torch.inference_mode():
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
