import sys
import os
import uvicorn
import asyncio
import time
import json
import subprocess
import argparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from starlette.concurrency import run_in_threadpool
import mido
import torch
import pretty_midi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Command Line Arguments ---
parser = argparse.ArgumentParser(description="Orpheus Music API")
parser.add_argument("--fp16", action="store_true", help="Use FP16 precision (Recommended for Steam Deck/GPUs)")
parser.add_argument("--port", type=int, default=9000, help="API Port")
parser.add_argument("--host", type=str, default="0.0.0.0", help="API Host")
args, unknown = parser.parse_known_args()

# Settings
ORPHEUS_MODEL_PATH = os.environ.get("ORPHEUS_MODEL_PATH", "models/Orpheus-Large/orpheus_large.pth")
OUTPUT_DIR = Path("./outputs/api_generated")
SOUNDFONT_PATH = os.environ.get("SOUNDFONT_PATH", "soundfonts/FluidR3_GM/FluidR3_GM.sf2")

# ── Backend Import ───────────────────────────────────────────────────────────
from orpheus_backend import OrpheusBackend, decode_orpheus_tokens

# ── Core imports ─────────────────────────────────────────────────────────────
from core.parser import parse_prompt
from core.style_config import STYLE_DATA
from llm.planner import create_song_plan

# Global state
backend = None

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global backend
    print(f"\n[API] Initializing ORPHEUS-LARGE (748M) from '{ORPHEUS_MODEL_PATH}'...", flush=True)
    try:
        backend = OrpheusBackend(ORPHEUS_MODEL_PATH, use_fp16=args.fp16)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[API] Orpheus engine ready. (Precision: {'FP16' if args.fp16 else 'FP32'})", flush=True)
        yield
    except Exception as e:
        print(f"[API] CRITICAL ERROR loading Orpheus: {e}")
        yield
    finally:
        print("[API] Shutting down...", flush=True)

app = FastAPI(lifespan=lifespan)

class PlanOnlyRequest(BaseModel):
    plan: dict
    parallel_tracks: int = -1

class FullSongRequest(BaseModel):
    user_prompt: str

class ConvertRequest(BaseModel):
    midi_path: str

# ── Generation Endpoint ──────────────────────────────────────────────────────

@app.post("/generate_from_plan")
async def generate_from_plan(req: PlanOnlyRequest):
    global backend
    plan = req.plan
    genre = plan.get("genre", "ebm").lower()
    bpm  = float(plan.get("bpm", 140))
    
    style_cfg = STYLE_DATA.get(genre, STYLE_DATA.get("ebm", {}))
    velocity_base = style_cfg.get("pipeline", {}).get("velocity_base", 90)

    tasks = []
    current_bar_offset = 0
    
    for section in plan.get("sections", []):
        section_name = section.get("name", "Section")
        section_bars = int(section.get("bars", 32))
        
        for track in section.get("tracks", []):
            if track.get("midi_prompt", "").lower() == "silence": continue
            
            out_filename = f"{track.get('id')}_{section_name.replace(' ', '_')}_{int(time.time())}.mid"
            tasks.append({
                "out_path": OUTPUT_DIR / out_filename,
                "name": track.get("name"),
                "id": track.get("id"),
                "is_drum": bool(track.get("is_drum", False)),
                "program": int(track.get("program", 0)),
                "start_time": current_bar_offset * (60.0 / bpm * 4.0),
                "duration": section_bars * (60.0 / bpm * 4.0)
            })
        current_bar_offset += section_bars

    valid_results = []
    for t in tasks:
        print(f"[API] Generating {t['name']} with Orpheus...", flush=True)
        seed = [512, 15, 128+100, 100] # Standard 4-token seed
        
        try:
            tokens = await run_in_threadpool(backend.generate, prompt_tokens=seed, max_len=256)
            mid = decode_orpheus_tokens(tokens)
            mid.save(str(t["out_path"]))
            valid_results.append(t)
        except Exception as e:
            print(f"  ✗ Orpheus error: {e}")

    if not valid_results:
        return {"status": "error", "message": "No tracks generated."}

    # Merge Logic
    merged_midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    instr_map = {}
    for i, t_def in enumerate(plan.get("sections", [{}])[0].get("tracks", [])):
        is_d = bool(t_def.get("is_drum", False))
        inst = pretty_midi.Instrument(program=int(t_def.get("program", 0)), is_drum=is_d, name=t_def.get("name"))
        inst.track_id = t_def.get("id", f"track_{i}")
        merged_midi.instruments.append(inst)
        instr_map[inst.track_id] = inst

    for res in valid_results:
        try:
            clip = pretty_midi.PrettyMIDI(str(res["out_path"]))
            target = instr_map.get(res["id"])
            if not target: continue
            for inst in clip.instruments:
                for note in inst.notes:
                    new_note = pretty_midi.Note(
                        velocity=min(127, int(note.velocity * (velocity_base/100.0))),
                        pitch=note.pitch,
                        start=res["start_time"] + note.start,
                        end=res["start_time"] + note.end
                    )
                    target.notes.append(new_note)
        except: continue

    safe_title = plan.get("title", "song").replace(" ", "_")
    final_path = OUTPUT_DIR / f"{safe_title}_{int(time.time())}_merged.mid"
    merged_midi.write(str(final_path))

    return {"status": "success", "midi_path": str(final_path), "engine": "Orpheus-Large"}

@app.post("/convert")
async def convert_midi(req: ConvertRequest):
    if not os.path.exists(req.midi_path):
        raise HTTPException(status_code=404, detail="MIDI file not found")
    wav_path = req.midi_path.replace(".mid", ".wav")
    try:
        cmd = ["fluidsynth", "-ni", "-F", wav_path, SOUNDFONT_PATH, req.midi_path]
        subprocess.run(cmd, check=True, capture_output=True)
        return {"status": "success", "wav_path": wav_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/generate_full")
async def generate_full(req: FullSongRequest):
    genre, topic = parse_prompt(req.user_prompt)
    plan = await create_song_plan(topic, genre)
    return {"status": "success", "genre": genre, "topic": topic, "plan": plan}

@app.get("/download")
async def download_file(path: str):
    if os.path.exists(path):
        return FileResponse(path, filename=os.path.basename(path))
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)
