import sys
import os
import subprocess
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

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
            if "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
                print("Setting HSA_OVERRIDE_GFX_VERSION=10.3.0 for Steam Deck compatibility.", flush=True)
                os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
    except Exception:
        pass

detect_hardware()

from contextlib import asynccontextmanager

# Check for CPU override
if os.environ.get("FORCE_CPU") == "1":
    print("FORCE_CPU is set. Forcing PyTorch to use CPU.", flush=True)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HIP_VISIBLE_DEVICES"] = ""

# Add MIDI-LLM repo to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "MIDI-LLM")))

from generate_transformers import prepare_hf_model, generate_from_prompts_hf
from transformers import AutoTokenizer

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    print("Loading MIDI-LLM model...", flush=True)
    print(f"Using model path: {model_path}", flush=True)
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
    # Clean up the model and release the resources
    print("Shutting down...", flush=True)

app = FastAPI(lifespan=lifespan)

class GenerateRequest(BaseModel):
    prompt: str
    temperature: float = 1.0

class ConvertRequest(BaseModel):
    midi_path: str

# Global state for the model
model = None
tokenizer = None
model_path = "models/MIDI-LLM"
output_dir = Path("./outputs/api_generated")

# Removed @app.on_event("startup") def load_model()

@app.post("/generate")
def generate(req: GenerateRequest):
    print(f"Received prompt: {req.prompt}")
    
    stats = generate_from_prompts_hf(
        model=model,
        tokenizer=tokenizer,
        prompts=[req.prompt],
        output_dir=output_dir,
        model_path=model_path,
        synthesize=False,         # Generation only
        temperature=req.temperature,
        top_p=0.98,
        max_tokens=2046,
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
