import sys
import os
import subprocess
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from starlette.concurrency import run_in_threadpool

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Automatic Hardware Detection for Steam Deck / AMD
def detect_hardware():
    # Check for AMD GPU
    try:
        is_amd = False
        if os.path.exists("/sys/class/drm/card0/device/vendor"):
            with open("/sys/class/drm/card0/device/vendor", "r") as f:
                if "0x1002" in f.read():
                    is_amd = True
        
        if not is_amd:
            # Fallback to lspci
            res = subprocess.run(["lspci"], capture_output=True, text=True)
            if "AMD" in res.stdout or "ATI" in res.stdout:
                is_amd = True
        
        if is_amd:
            print("Detected AMD GPU/Steam Deck hardware.", flush=True)
            
            # VRAM Check for AMD
            vram_limit_met = True
            if os.path.exists("/sys/class/drm/card0/device/mem_info_vram_total"):
                with open("/sys/class/drm/card0/device/mem_info_vram_total", "r") as f:
                    vram_bytes = int(f.read().strip())
                    vram_gb = vram_bytes / (1024**3)
                    print(f"AMD VRAM: {vram_gb:.2f} GB")
                    if vram_gb < 3.5: # 4GB-ish limit
                        print("AMD VRAM is too low (< 4GB). Falling back to CPU mode.")
                        vram_limit_met = False
            
            if vram_limit_met:
                if "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
                    print("Setting HSA_OVERRIDE_GFX_VERSION=10.3.0 for Steam Deck compatibility.", flush=True)
                    os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
            else:
                os.environ["FORCE_CPU"] = "1"

    except Exception as e:
        print(f"Hardware detection warning: {e}")

detect_hardware()

from contextlib import asynccontextmanager

# Check for CPU override
if os.environ.get("FORCE_CPU") == "1":
    print("FORCE_CPU is set or VRAM is too low. Forcing PyTorch to use CPU.", flush=True)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HIP_VISIBLE_DEVICES"] = ""

# Add MIDI-LLM repo to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "MIDI-LLM")))

from generate_transformers import prepare_hf_model, generate_from_prompts_hf
from transformers import AutoTokenizer

from llm.prompt_expander import expand_prompt
from llm.planner import create_song_plan
from core.parser import parse_prompt

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    print("Loading MIDI-LLM model...", flush=True)
    print(f"Using model path: {model_path}", flush=True)
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_path, 
            pad_token="<|eot_id|>",
            local_files_only=True
        )
        print("Tokenizer loaded. Loading model weights...", flush=True)
        model = prepare_hf_model(model_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        print("Model loaded successfully!", flush=True)
        yield
    finally:
        # Clean up the model and release the resources
        print("Shutting down and releasing resources...", flush=True)

app = FastAPI(lifespan=lifespan)

class GenerateRequest(BaseModel):
    prompt: str
    temperature: float = 1.0

class PlanRequest(BaseModel):
    genre: str
    topic: str

class PlanOnlyRequest(BaseModel):
    plan: dict

class FullSongRequest(BaseModel):
    user_prompt: str # e.g. "<futurepop> neon dreams"

class ConvertRequest(BaseModel):
    midi_path: str

# Global state for the model
model = None
tokenizer = None
model_path = "models/MIDI-LLM"
output_dir = Path("./outputs/api_generated")

# Semaphore to limit concurrent generation tasks
generation_semaphore = asyncio.Semaphore(2)

# Removed @app.on_event("startup") def load_model()

@app.post("/generate")
async def generate(req: GenerateRequest):
    print(f"Received prompt: {req.prompt}")
    
    try:
        async with generation_semaphore:
            # Run the synchronous generation in a threadpool to remain responsive
            stats = await run_in_threadpool(
                generate_from_prompts_hf,
                model=model,
                tokenizer=tokenizer,
                prompts=[req.prompt],
                output_dir=output_dir,
                model_path=model_path,
                synthesize=False,         # Generation only
                temperature=req.temperature,
                top_p=0.98,
                max_tokens=8192,
                n_outputs=1
            )
        
        if stats['output_files']:
            midi_file = stats['output_files'][0]
            return {
                "status": "success", 
                "midi_path": str(midi_file)
            }
        else:
            return {"status": "error", "message": "Failed to generate MIDI."}
            
    except asyncio.CancelledError:
        print(f"Generation cancelled for prompt: {req.prompt}")
        # Re-raise to allow Starlette to handle it, but we've logged it
        raise
    except Exception as e:
        print(f"Error during generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plan")
async def plan_song(req: PlanRequest):
    """
    Expands a topic and creates a full JSON song plan using Ollama.
    """
    print(f"Planning song for Genre: {req.genre} | Topic: {req.topic}")
    try:
        expanded = await run_in_threadpool(expand_prompt, req.genre, req.topic)
        plan = await run_in_threadpool(create_song_plan, expanded, req.genre)
        return {"status": "success", "plan": plan}
    except Exception as e:
        print(f"Planning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_full")
async def generate_full(req: FullSongRequest):
    """
    The complete pipeline: Parse -> Expand -> Plan -> Return Plan
    (Note: This returns the plan; the client can then call /generate for each clip)
    """
    print(f"Full pipeline request: {req.user_prompt}")
    try:
        genre, topic = parse_prompt(req.user_prompt)
        expanded = await run_in_threadpool(expand_prompt, genre, topic)
        plan = await run_in_threadpool(create_song_plan, expanded, genre)
        return {
            "status": "success",
            "genre": genre,
            "topic": topic,
            "plan": plan
        }
    except Exception as e:
        print(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_from_plan")
async def generate_from_plan(req: PlanOnlyRequest):
    """
    Takes a JSON plan and generates all MIDI clips for it.
    """
    plan = req.plan
    prompts = []
    track_info = []

    print(f"Generating MIDI from plan: {plan.get('title', 'untitled')}")
    
    # Extract all prompts from the plan sections/tracks
    for section in plan.get("sections", []):
        for track in section.get("tracks", []):
            raw_prompt = track.get("midi_prompt", "")
            # Forensic enhancement
            enhanced_prompt = (
                f"{raw_prompt}. Style: {track.get('grid', '1/16 notes')}. "
                f"Density: {track.get('density', 0.5)}. "
                f"Max Polyphony: {track.get('polyphony', 1)}. "
                f"Range: MIDI {track.get('pitch_range', [36, 84])}."
            )
            prompts.append(enhanced_prompt)
            track_info.append({
                "section": section.get("name"),
                "track": track.get("name")
            })

    if not prompts:
        return {"status": "error", "message": "No tracks found in plan."}

    try:
        async with generation_semaphore:
            # Generate all clips in batch
            stats = await run_in_threadpool(
                generate_from_prompts_hf,
                model=model,
                tokenizer=tokenizer,
                prompts=prompts,
                output_dir=output_dir,
                model_path=model_path,
                synthesize=False,
                temperature=1.0,
                top_p=0.98,
                max_tokens=8192,
                n_outputs=1
            )
        
        results = []
        for i, midi_path in enumerate(stats.get('output_files', [])):
            results.append({
                "info": track_info[i],
                "midi_path": str(midi_path)
            })
            
        return {
            "status": "success",
            "files": results
        }
    except Exception as e:
        print(f"Batch generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert")
def convert(req: ConvertRequest):
    print(f"Converting MIDI to WAV: {req.midi_path}")
    
    if not os.path.exists(req.midi_path):
        return {"status": "error", "message": "MIDI file not found."}
        
    wav_path = req.midi_path.replace(".mid", ".wav")
    soundfont_path = "soundfonts/FluidR3_GM.sf2"
    
    cmd = [
        "fluidsynth",
        "-ni",
        "-F", wav_path,
        "-r", "44100",
        soundfont_path,
        req.midi_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return {
            "status": "success",
            "wav_path": wav_path
        }
    except Exception as e:
        return {"status": "error", "message": f"Conversion failed: {str(e)}"}

@app.get("/download")
def download(path: str):
    """
    Serves a file for the client to download.
    """
    if os.path.exists(path):
        return FileResponse(path, filename=os.path.basename(path))
    return {"status": "error", "message": "File not found."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
