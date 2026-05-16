import sys
import os
import subprocess
import uvicorn
import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from starlette.concurrency import run_in_threadpool
import mido

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import torch

# ── Hardware & Library Safety Overrides ─────────────────────────────────────
# Prevent SIGILL (Illegal Instruction) by disabling advanced math optimizations
# and limiting threading overhead.
os.environ["MKL_DEBUG"] = "1"
os.environ["OPENBLAS_CORETYPE"] = "Generic"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
torch.set_num_threads(1)

# Suppress PipeWire warnings from FluidSynth
os.environ["PIPEWIRE_LOG_LEVEL"] = "0"

# Automatic Hardware Detection
def detect_hardware():
    try:
        is_amd = False
        if os.path.exists("/sys/class/drm/card0/device/vendor"):
            with open("/sys/class/drm/card0/device/vendor", "r") as f:
                if "0x1002" in f.read():
                    is_amd = True
        if is_amd:
            print("Detected AMD GPU hardware.", flush=True)
            if "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
                os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
    except Exception as e:
        print(f"Hardware detection warning: {e}")

detect_hardware()

from contextlib import asynccontextmanager

# ── Core imports (preserved from original) ───────────────────────────────────
from core.parser import parse_prompt
from core.style_config import STYLE_DATA
from core.scheduler import create_schedule

# ── NotaGen backend ───────────────────────────────────────────────────────────
from notagen.notagen_backend import load_model, generate_section, build_notagen_prompt
from notagen.abc_to_midi import count_max_simultaneous


# ── LLM planner (unchanged) ───────────────────────────────────────────────────
from llm.planner import create_song_plan

# SETTINGS
NOTAGEN_MODEL_SIZE = os.environ.get("NOTAGEN_MODEL_SIZE", "medium")
NOTAGEN_MODEL_PATH = os.environ.get("NOTAGEN_MODEL_PATH", "models/NotaGen-medium")
OUTPUT_DIR = Path("./outputs/api_generated")

# Robust parsing for environment variables
def get_env_int(name, default):
    val = os.environ.get(name)
    if not val or not val.strip():
        return default
    try:
        return int(val)
    except ValueError:
        return default

def ensure_number(val, default=120):
    """Ensures the value is a number (float/int). Handles lists and strings."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, list) and len(val) > 0:
        return ensure_number(val[0], default)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return float(default)
    return float(default)

def ensure_bool(val, default=False):
    """Ensures the value is a boolean. Handles strings like 'true', 'false', 'yes', 'no'."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        val = val.lower().strip()
        if val in ("true", "yes", "1", "y"): return True
        if val in ("false", "no", "0", "n"): return False
    if isinstance(val, (int, float)):
        return bool(val)
    return default

MAX_PARALLEL_TRACKS = get_env_int("MAX_PARALLEL_TRACKS", 2)

# Global state
model = None
tokenizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    print(f"Loading NotaGen-{NOTAGEN_MODEL_SIZE} model from '{NOTAGEN_MODEL_PATH}'...", flush=True)
    try:
        # load_model returns (model, patchilizer, cfg)
        _model, _patchilizer, _cfg = load_model(NOTAGEN_MODEL_PATH, size=NOTAGEN_MODEL_SIZE)
        model     = _model
        tokenizer = (_patchilizer, _cfg)   # tuple passed through to generate_section
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"NotaGen {NOTAGEN_MODEL_SIZE} model loaded successfully!", flush=True)
        yield
    finally:
        print("Shutting down...", flush=True)

app = FastAPI(lifespan=lifespan)

# ── Request schemas (identical to original for batch-client compatibility) ────
class GenerateRequest(BaseModel):
    prompt: str                   # Accepts: "Period|Composer|Instrumentation"
    temperature: float = 0.9

class PlanOnlyRequest(BaseModel):
    plan: dict
    parallel_tracks: int = -1

class ConvertRequest(BaseModel):
    midi_path: str

class FullSongRequest(BaseModel):
    user_prompt: str

# Global semaphore for standard /generate endpoint
generation_semaphore = asyncio.Semaphore(1)


# ── /generate  (simple single-prompt test endpoint) ───────────────────────────
@app.post("/generate")
async def generate(req: GenerateRequest):
    """
    Generate a MIDI from a raw NotaGen prompt for testing.
    Prompt format: "Period|Composer|Instrumentation"
    e.g. "Romantic|Chopin, Frédéric|solo piano"
    """
    async with generation_semaphore:
        timestamp = int(time.time())
        out_path = OUTPUT_DIR / f"test_{timestamp}.mid"

        result = await run_in_threadpool(
            generate_section,
            model=model,
            tokenizer=tokenizer,
            style_desc=req.prompt,
            instrument_name="Test",
            bpm=120.0,
            section_name="Test",
            bars=8,
            polyphony_limit=8,
            grid="1/16",
            density=0.5,
            pitch_range=None,
            transition="normal",
            is_drum=False,
            output_path=out_path,
            instrument_program=0,
        )

    if result and result.exists():
        return {"status": "success", "midi_path": str(result)}
    return {"status": "error", "message": "Failed to generate MIDI."}


# ── /generate_full  (plan → genre/topic extraction, unchanged) ───────────────
@app.post("/generate_full")
async def generate_full(req: FullSongRequest):
    print(f"Full pipeline request: {req.user_prompt}")
    try:
        genre, topic = parse_prompt(req.user_prompt)
        plan = await run_in_threadpool(create_song_plan, topic, genre)
        return {"status": "success", "genre": genre, "topic": topic, "plan": plan}
    except Exception as e:
        print(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── /generate_from_plan  (main generation endpoint) ───────────────────────────
@app.post("/generate_from_plan")
async def generate_from_plan(req: PlanOnlyRequest):
    plan = req.plan
    bpm  = ensure_number(plan.get("bpm"), 120)

    # ── Resolve genre-level defaults from core/style_config.py ───────────────
    genre = plan.get("genre", "ebm").lower()
    style_cfg = STYLE_DATA.get(genre, STYLE_DATA["ebm"])
    pipeline_cfg = style_cfg.get("pipeline", {})

    genre_default_poly  = pipeline_cfg.get("max_polyphony", 4)
    genre_drum_density  = pipeline_cfg.get("drum_density",  1.0)
    genre_melody_density = pipeline_cfg.get("melody_density", 0.3)
    genre_humanization  = pipeline_cfg.get("humanization",  0.0)
    genre_bass_rep      = pipeline_cfg.get("bass_repetition", 0.9)
    genre_velocity_base = pipeline_cfg.get("velocity_base", 80)  # Genre-level velocity

    beat_length = 60.0 / bpm
    bar_length  = beat_length * 4.0

    print(f"\nGenerating from plan: '{plan.get('title', 'untitled')}' "
          f"[{genre.upper()} | {bpm} BPM | poly_default={genre_default_poly}]", flush=True)

    # ── Instrument & Drum memory for continuity across sections ──────────────
    instrument_history: dict = {}
    drum_style_memory: dict  = {}  # Ensures drums "play the same notes" throughout

    # ── Collect all generation tasks ─────────────────────────────────────────
    tasks = []          # (out_path, start_time, duration, track_name, is_drum)
    current_bar_offset = 0

    for i, section in enumerate(plan.get("sections", [])):
        section_name  = section.get("name", "Unknown")
        section_bars  = int(ensure_number(section.get("bars"), 8))
        start_time    = current_bar_offset * bar_length
        duration      = section_bars * bar_length
        transition    = section.get("transition", "normal")

        # section_density: try to match section name to a density range
        section_density_map = pipeline_cfg.get("section_density", {})
        matched_density_range = None
        for key in section_density_map:
            if key.lower() in section_name.lower():
                matched_density_range = section_density_map[key]
                break

        print(f"\n[API] Section {i+1}: '{section_name}' "
              f"({section_bars} bars, t={start_time:.2f}s, transition={transition})", flush=True)

        for track in section.get("tracks", []):
            instr_name = track.get("name", "synthesizer")
            track_id   = track.get("id", "unknown")
            is_drum    = ensure_bool(track.get("is_drum", False))
            raw_style  = track.get("midi_prompt", "").strip()

            # ── MANDATORY DRUMS LOGIC ───────────────────────────────────────
            # Drums/Claps must always be present. If raw_style is "silence", 
            # we override it with a default prompt for that instrument.
            is_mandatory_drum = is_drum or any(k in instr_name.lower() for k in ["drum", "clap", "snare", "kick", "percussion"])
            
            if not raw_style or raw_style.lower() == "silence":
                if is_mandatory_drum:
                    raw_style = f"Standard {instr_name} pattern"
                    print(f"  → Overriding silence for mandatory drum: {instr_name}", flush=True)
                else:
                    # Skip non-drum silence
                    print(f"  → Skipping silent track: {instr_name}", flush=True)
                    continue

            # ── CONSISTENCY LOGIC (Same notes/patterns) ─────────────────────
            # If it's a drum, reuse the style/pattern from the first section
            if is_mandatory_drum:
                if track_id not in drum_style_memory:
                    drum_style_memory[track_id] = raw_style
                else:
                    raw_style = drum_style_memory[track_id]
            # ────────────────────────────────────────────────────────────────

            # ── Resolve polyphony ──────────────────────────────────────────
            # Priority: track-level → genre-level default from style_config
            track_poly = int(ensure_number(track.get("polyphony", genre_default_poly)))
            track_poly = max(1, track_poly) # Ensure at least 1
            if is_drum:
                track_poly = 1   # drums always mono

            # ── Resolve density ────────────────────────────────────────────
            track_density = float(track.get("density", 0.5))
            if matched_density_range:
                import random
                lo, hi = matched_density_range
                track_density = random.uniform(lo, hi)
            # Override with genre-level drum/melody density where appropriate
            if is_drum:
                track_density *= genre_drum_density
            else:
                track_density *= genre_melody_density if "bass" not in instr_name.lower() else genre_bass_rep

            # ── Other track params from plan ───────────────────────────────
            grid = track.get("grid", "1/16")

            # ── Pitch range: style_config takes priority over LLM output ───
            # Look up the instrument's defined range by name (fuzzy match).
            # This ensures each instrument stays in its musically correct register.
            genre_instr_ranges = style_cfg.get("instrument_ranges", {})
            pitch_range = None
            # Exact match first, then partial match
            if instr_name in genre_instr_ranges:
                pitch_range = genre_instr_ranges[instr_name]
            else:
                instr_lower = instr_name.lower()
                for key, rng in genre_instr_ranges.items():
                    if key.lower() in instr_lower or instr_lower in key.lower():
                        pitch_range = rng
                        break
            # Fallback to LLM-provided value if no style_config match
            if not pitch_range:
                pitch_range = track.get("pitch_range", []) or None

            # GM program — try to get from plan, default sensibly
            program = track.get("program", 0)

            # ── Instrument memory (recall + update) ────────────────────────
            recall_note = ""
            if track_id in instrument_history:
                prev = instrument_history[track_id]
                recall_note = f" [RECALL: prev={prev['style']}, range={prev['range']}]"
            instrument_history[track_id] = {"style": raw_style, "range": pitch_range}

            # ── Density description for logging ───────────────────────────
            if track_density <= 0.2:   density_desc = "extremely sparse"
            elif track_density <= 0.4: density_desc = "sparse"
            elif track_density <= 0.6: density_desc = "moderate"
            elif track_density <= 0.8: density_desc = "busy"
            else:                      density_desc = "very dense"

            print(f"  → '{instr_name}' | drum={is_drum} | poly={track_poly} | "
                  f"density={track_density:.2f}({density_desc}) | grid={grid}"
                  f"{recall_note}", flush=True)

            # ── Build output path (mirrors original _prompt_N structure) ───
            timestamp_str = int(time.time() * 1000)
            prompt_idx    = len(tasks) + 1
            out_dir       = OUTPUT_DIR / f"{timestamp_str}_prompt_{prompt_idx}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path      = out_dir / "best_variation.mid"

            tasks.append({
                "out_path":    out_path,
                "start_time":  start_time,
                "duration":    duration,
                "track_name":  instr_name,
                "track_id":    track_id,  # Added track_id for unique merging
                "is_drum":     is_drum,
                "style_desc":  raw_style,
                "bpm":         bpm,
                "section_name": section_name,
                "bars":        section_bars,
                "polyphony_limit": track_poly,
                "grid":        grid,
                "density":     track_density,
                "pitch_range": pitch_range,
                "transition":  transition,
                "program":     program,
                "velocity_base": genre_velocity_base,
            })

        current_bar_offset += section_bars

    if not tasks:
        return {"status": "error", "message": "No active tracks found in plan."}

    # ── Run generation sequentially (CPU-constrained) ─────────────────────────
    valid_results = []  # (out_path, start_time, duration, track_name, is_drum)

    for t in tasks:
        result = await run_in_threadpool(
            generate_section,
            model=model,
            tokenizer=tokenizer,
            style_desc=t["style_desc"],
            instrument_name=t["track_name"],
            bpm=t["bpm"],
            section_name=t["section_name"],
            bars=t["bars"],
            polyphony_limit=t["polyphony_limit"],
            grid=t["grid"],
            density=t["density"],
            pitch_range=t["pitch_range"],
            transition=t["transition"],
            is_drum=t["is_drum"],
            output_path=t["out_path"],
            instrument_program=t["program"],
            velocity_base=t["velocity_base"],
        )
        if result and Path(result).exists():
            valid_results.append({
                "path": result,
                "start_time": t["start_time"],
                "duration": t["duration"],
                "name": t["track_name"],
                "id": t["track_id"],
                "is_drum": t["is_drum"],
                "limit": t["polyphony_limit"],
                "program": t["program"] # Store program
            })
        else:
            print(f"  ✗ Generation failed for '{t['track_name']}'", flush=True)

    if not valid_results:
        return {"status": "error", "message": "All tracks failed to generate."}

    # ── Polyphony forensic report ─────────────────────────────────────────────
    print("\n[API] Polyphony Audit:", flush=True)
    for res in valid_results:
        try:
            actual = count_max_simultaneous(Path(res["path"]))
            status = "✓" if actual <= res["limit"] else "✗ VIOLATION"
            print(f"  {status} {res['name']} ({res['id']}): {actual}/{res['limit']} simultaneous notes", flush=True)
        except Exception as e:
            print(f"  ? {res['name']}: audit error: {e}", flush=True)

    # ── Merge all tracks into one multi-track MIDI ───────────────────────────
    import pretty_midi

    timestamp = int(time.time())
    safe_title = plan.get("title", "untitled").replace(" ", "_")
    merged_filename = f"{safe_title}_{timestamp}_merged.mid"
    merged_path = OUTPUT_DIR / merged_filename

    print(f"\n[API] Merging {len(valid_results)} tracks → {merged_path}", flush=True)

    song = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    # 1. PRE-INITIALIZE ALL INSTRUMENTS FROM THE PLAN
    # This ensures the MIDI file has the correct track count and order
    # even if some instruments are silent.
    all_instrument_defs = []
    # Collect all unique track definitions from the first section as a template
    if plan.get("sections"):
        all_instrument_defs = plan["sections"][0].get("tracks", [])

    for i, t_def in enumerate(all_instrument_defs):
        name = t_def.get("name", "Synth")
        t_id = t_def.get("id", f"track_{i}")
        is_d = ensure_bool(t_def.get("is_drum", False))
        prog = t_def.get("program", 0)
        
        inst = pretty_midi.Instrument(program=prog, is_drum=is_d, name=name)
        inst.track_id = t_id # Custom attribute
        
        # ADD KEEP-ALIVE NOTE: A zero-velocity note at the very end 
        # prevents DAWs and pretty_midi from pruning the 'empty' track.
        total_song_duration = current_bar_offset * bar_length
        keep_alive = pretty_midi.Note(
            velocity=0, pitch=0, start=total_song_duration - 0.1, end=total_song_duration
        )
        inst.notes.append(keep_alive)
        song.instruments.append(inst)

    # 2. FILL INSTRUMENTS WITH GENERATED NOTES
    for res in valid_results:
        path = res["path"]
        start_time = res["start_time"]
        duration = res["duration"]
        track_name = res["name"]
        track_id = res["id"]
        is_drum = res["is_drum"]
        program = res["program"]

        if not os.path.exists(path):
            continue
        try:
            clip = pretty_midi.PrettyMIDI(str(path))

            # Time-scale the clip to the target BPM
            clip_bpm = 120.0
            tempo_times, tempos = clip.get_tempo_changes()
            if len(tempo_times) > 0:
                clip_bpm = tempos[0]
            time_scale = clip_bpm / bpm

            # Find the pre-initialized instrument
            target_inst = None
            for existing in song.instruments:
                if getattr(existing, "track_id", None) == track_id:
                    target_inst = existing
                    break
            
            # Fallback (should not happen with pre-init)
            if not target_inst:
                target_inst = pretty_midi.Instrument(
                    program=program, is_drum=is_drum, name=track_name
                )
                target_inst.track_id = track_id
                song.instruments.append(target_inst)

            max_end = start_time + duration
            for inst in clip.instruments:
                for note in inst.notes:
                    scaled_start = note.start * time_scale
                    scaled_end   = note.end   * time_scale
                    if scaled_start < duration:
                        new_note = pretty_midi.Note(
                            velocity=note.velocity,
                            pitch=note.pitch,
                            start=start_time + scaled_start,
                            end=min(start_time + scaled_end, max_end),
                        )
                        target_inst.notes.append(new_note)

        except Exception as e:
            print(f"  ✗ Error merging {path}: {e}", flush=True)

    song.write(str(merged_path))
    print(f"[API] Done. Merged MIDI: {merged_path}", flush=True)

    return {
        "status": "success",
        "midi_path": str(merged_path),
        "track_count": len(song.instruments),
    }


# ── /convert  (FluidSynth WAV rendering, unchanged) ──────────────────────────
@app.post("/convert")
def convert(req: ConvertRequest):
    if not os.path.exists(req.midi_path):
        return {"status": "error", "message": "File not found."}
    wav_path = req.midi_path.replace(".mid", ".wav")
    cmd = ["fluidsynth", "-ni", "-F", wav_path, "-r", "44100",
           "soundfonts/FluidR3_GM.sf2", req.midi_path]
    try:
        subprocess.run(cmd, check=True)
        return {"status": "success", "wav_path": wav_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── /download  (file download, unchanged) ─────────────────────────────────────
@app.get("/download")
def download(path: str):
    if os.path.exists(path):
        return FileResponse(path, filename=os.path.basename(path))
    return {"status": "error", "message": "File not found."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
