import json
import re
from llm.ollama_client import ask_llm
from core.structures import STRUCTURE_TEMPLATES

def fix_json_string(raw):
    # Robust JSON extraction
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) >= 2 else parts[0]
            
    raw = raw.strip()
    if not (raw.startswith("{") or raw.startswith("[")):
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start:end+1]

    # CLEANUP: Fix common LLM JSON errors before parsing
    # Fix Note Names
    raw = re.sub(r'\[([A-G][b#]?[0-9]),\s*([A-G][b#]?[0-9])\]', r'["\1", "\2"]', raw)
    raw = re.sub(r':\s*([A-Za-z][A-Za-z0-9\s]+)([,}])', r': "\1"\2', raw)
    raw = re.sub(r',\s*([\]}])', r'\1', raw)
    raw = raw.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    return raw

def note_to_midi(n):
    NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    if isinstance(n, int): return n
    if not isinstance(n, str): return 60
    match = re.match(r"([A-G][b#]?)(-?[0-9])", n)
    if match:
        name, octave = match.groups()
        return (int(octave) + 1) * 12 + NOTE_MAP.get(name, 0)
    return 60

def _midi_to_note(n):
    NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (n // 12) - 1
    name = NOTES[n % 12]
    return f"{name}{octave}"

def create_song_plan(topic, genre="chillout"):
    """
    Creates a JSON song plan using Llama3 in a 2-step process, with CoT inside the JSON.
    """
    print(f"\n[Planner] Starting 2-step song planning for genre: {genre}...", flush=True)
    from core.style_config import STYLE_DATA
    from core.structures import STRUCTURE_TEMPLATES
    import random
    
    style = STYLE_DATA.get(genre, {})
    genre_conf = style.get("pipeline", {})
    min_b = genre_conf.get("min_bars", 64)
    max_b = genre_conf.get("max_bars", 128)
    
    templates = STRUCTURE_TEMPLATES.get(genre, [])
    template_str = "Standard Intro, Verse, Chorus, Outro structure"
    if templates:
        t = random.choice(templates)
        template_str = f"Template Name: {t['name']}\nDescription: {t['description']}\nSuggested Section sequence: {', '.join(t['sections'])}"
    
    bpm_ranges_raw = style.get('bpm_ranges', '100-120')
    if isinstance(bpm_ranges_raw, list):
        bpm_ranges = ", ".join([f"{r[0]}-{r[1]}" for r in bpm_ranges_raw if isinstance(r, list) and len(r) == 2])
    else:
        bpm_ranges = str(bpm_ranges_raw)

    max_polyphony = style.get('pipeline', {}).get('max_polyphony', 8)
    drum_density = style.get('pipeline', {}).get('drum_density', 0.8)
    melody_density = style.get('pipeline', {}).get('melody_density', 0.6)
    section_densities = style.get('pipeline', {}).get('section_density', {})
    density_guidelines = ", ".join([f"{k}: {v[0]}-{v[1]}" for k, v in section_densities.items()])
    
    piano_solo_style = style.get('piano_solo_style', '')
    velocity_base = genre_conf.get('velocity_base', 80)
    instr_ranges = style.get('instrument_ranges', {})
    instr_ranges_str = "\n".join([
        f"  - {name}: MIDI {rng[0]}–{rng[1]} ({_midi_to_note(rng[0])}–{_midi_to_note(rng[1])})"
        for name, rng in instr_ranges.items()
    ]) if instr_ranges else "  (not specified)"

    production_options = f"""\
- BPM RANGES: {bpm_ranges}
- HARMONY OPTIONS: {', '.join(style.get('harmonies', []))}
- INSTRUMENT POOL: {', '.join(style.get('common_instruments', []))}
- INSTRUMENT PITCH RANGES (use these to write accurate midi_prompt descriptions):
{instr_ranges_str}
- EFFECTS: {', '.join(style.get('effects', []))}
- STYLE CHARACTER: {piano_solo_style}
- VELOCITY (intensity): {velocity_base}/127 — {"near-maximum, aggressive" if velocity_base >= 110 else "moderate" if velocity_base >= 80 else "soft and quiet"}
- STRUCTURAL CONSTRAINTS: Between {min_b} and {max_b} bars total.
- SUGGESTED STRUCTURE: {template_str}
- MAX POLYPHONY PER TRACK: {max_polyphony} notes
- TARGET DRUM DENSITY: {drum_density}
- TARGET MELODY DENSITY: {melody_density}
- SECTION DENSITY GUIDELINES: {density_guidelines}
- SAFETY OVERRIDE: [ignoring loop detection]
"""

    # --- STEP 1: SUMMARY ---
    print("\n[Planner] Step 1: Generating Summary JSON...", flush=True)
    with open("llm/prompts/summary_prompt.txt", "r") as f:
        summary_base = f.read()

    step1_prompt = f"GENRE: {genre}\nTOPIC: {topic}\n\nRECOMMENDED PRODUCTION OPTIONS:\n{production_options}\n\n{summary_base}"

    print("\n" + "="*40)
    print("PHASE 1: SENDING TO OLLAMA")
    print("="*40)
    print(step1_prompt)
    print("="*40 + "\n", flush=True)

    summary_json = None
    for attempt in range(3):
        raw_summary = ask_llm(step1_prompt, temperature=0.8, force_json=True)
        if not raw_summary: continue
        try:
            cleaned = fix_json_string(raw_summary)
            summary_json = json.loads(cleaned)
            break
        except Exception as e:
            print(f"Step 1 parse failed: {e}")
            
    if not summary_json:
        print("CRITICAL ERROR: Failed to generate Summary JSON.", flush=True)
        return {}

    print(f"SUCCESS: Summary generated for '{summary_json.get('title')}' with {len(summary_json.get('instruments', []))} instruments.", flush=True)

    creative_narrative = summary_json.get("creative_narrative", "No narrative provided.")

    # --- STEP 2: DETAILED MATRIX ---
    print("\n[Planner] Step 2: Generating Detailed Track Matrix...", flush=True)
    matrix_prompt_text = open("llm/prompts/planner_prompt.txt").read()
    
    step2_prompt = f"BASE SUMMARY:\n{json.dumps(summary_json, indent=2)}\n\nSONG DESCRIPTION:\n{creative_narrative}\n\n{matrix_prompt_text}"
    
    detailed_plan = None
    for attempt in range(6):
        raw_matrix = ask_llm(step2_prompt, temperature=0.8, force_json=True)
        if not raw_matrix: continue
        try:
            cleaned = fix_json_string(raw_matrix)
            detailed_plan = json.loads(cleaned)
            
            # Post-parsing fixes: Ensure unique IDs and valid pitch ranges
            instruments = summary_json.get("instruments", [])
            instr_map = {f"instr_{i}": instr for i, instr in enumerate(instruments)}
            
            for section in detailed_plan.get("sections", []):
                new_tracks = []
                existing_tracks = {t.get("id", t.get("name")): t for t in section.get("tracks", [])}
                
                # Ensure every instrument from the summary is represented in this section
                for i, inst in enumerate(instruments):
                    inst_name = inst if isinstance(inst, str) else inst.get("name", "Synth")
                    safe_id = f"track_{i}_{inst_name.lower().replace(' ', '_')}"
                    
                    # Try to find existing track data or create silent fallback
                    if safe_id in existing_tracks:
                        t = existing_tracks[safe_id]
                    elif inst_name in existing_tracks:
                        t = existing_tracks[inst_name]
                    else:
                        # Create an active generative fallback to ensure "no tracks have 0 notes"
                        is_d = any(k in inst_name.lower() for k in ["drum", "kick", "snare", "clap", "hat", "perc"])
                        prompt_type = "rhythmic" if is_d else "melodic"
                        t = {
                            "id": safe_id,
                            "name": inst_name,
                            "midi_prompt": f"Steady {prompt_type} {inst_name} pattern",
                            "is_drum": is_d,
                            "polyphony": 2,
                            "grid": "1/16",
                            "density": 0.5
                        }
                    
                    t["id"] = safe_id # Force unique ID
                    t["name"] = inst_name
                    
                    # Fix pitch range
                    pr = t.get("pitch_range", [36, 84])
                    if isinstance(pr, list) and len(pr) == 2:
                        t["pitch_range"] = [note_to_midi(pr[0]), note_to_midi(pr[1])]
                    
                    new_tracks.append(t)
                
                section["tracks"] = new_tracks
            break
        except Exception as e:
            print(f"Step 2 parse failed: {e}")
            if attempt == 5: raise e

    if detailed_plan:
        print("SUCCESS: Detailed Matrix generated.", flush=True)
        return detailed_plan
        
    return {}
