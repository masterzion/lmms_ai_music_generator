import torch
import os
import json
import asyncio
from typing import List, Dict, Optional
from llm.ollama_client import call_ollama
from core.parser import parse_prompt
from core.style_config import STYLE_DATA

# PROMPT PATHS
SUMMARY_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "summary_prompt.txt")
PLANNER_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "planner_prompt.txt")

def midi_to_note(midi_num: int) -> str:
    """Helper to convert MIDI number to note name for the LLM's understanding."""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_num // 12) - 1
    note = notes[midi_num % 12]
    return f"{note}{octave}"

async def create_song_plan(user_topic: str, genre: str = "ebm") -> Dict:
    """
    Two-step song planning:
    1. Generate high-level summary (Theme, Instruments, Sections).
    2. Expand into a detailed Orpheus-compatible MIDI matrix.
    """
    genre_info = STYLE_DATA.get(genre.lower(), STYLE_DATA["ebm"])
    
    # Enrichment: Pass style-specific ranges and dissonance rules to the LLM
    style_context = f"""
    GENRE: {genre.upper()}
    DYNAMICS: {genre_info['pipeline']['velocity_base']} velocity, {genre_info['pipeline']['max_polyphony']} polyphony
    INSTRUMENT RANGES: {genre_info['instrument_ranges']}
    HARMONIC RULES: {genre_info['harmonies']}
    PIANO STYLE: {genre_info['piano_solo_style']}
    """

    # --- STEP 1: SUMMARY ---
    with open(SUMMARY_PROMPT_PATH, "r") as f:
        summary_base = f.read()
    
    summary_prompt = f"{summary_base}\n\nTOPIC: {user_topic}\nSTYLE CONTEXT: {style_context}"
    summary_text = await call_ollama(summary_prompt)
    
    # --- STEP 2: PLANNER ---
    with open(PLANNER_PROMPT_PATH, "r") as f:
        planner_base = f.read()
    
    full_prompt = f"{planner_base}\n\nSUMMARY:\n{summary_text}\n\n{style_context}"
    
    plan_json_str = await call_ollama(full_prompt)
    
    try:
        # Clean up common LLM markdown junk
        clean_json = plan_json_str.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
            
        plan = json.loads(clean_json)
        
        # Post-process Orpheus Seeds
        # If the LLM didn't provide a seed_note, we use a genre-appropriate default
        for section in plan.get("sections", []):
            for track in section.get("tracks", []):
                if "seed_note" not in track:
                    track["seed_note"] = genre_info["instrument_ranges"].get(track["name"], [36, 60])[0]
        
        return plan
    except Exception as e:
        print(f"[PLANNER ERROR] Failed to parse JSON: {e}")
        # Fallback to a very minimal plan if LLM fails
        return {"status": "error", "message": "JSON Parse Failure"}
