import sys
import os
import subprocess
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

# Add MIDI-LLM repo to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "MIDI-LLM")))

from generate_transformers import prepare_hf_model, generate_from_prompts_hf
from transformers import AutoTokenizer

app = FastAPI()

class GenerateRequest(BaseModel):
    prompt: str
    temperature: float = 1.0

class ConvertRequest(BaseModel):
    midi_path: str

# Global state for the model
model = None
tokenizer = None
model_path = "slseanwu/MIDI-LLM_Llama-3.2-1B"
output_dir = Path("./outputs/api_generated")

@app.on_event("startup")
def load_model():
    global model, tokenizer
    print("Loading MIDI-LLM model into VRAM...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, pad_token="<|eot_id|>")
    model = prepare_hf_model(model_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    print("Model loaded successfully!")

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
