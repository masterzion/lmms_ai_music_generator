import json

from llm.ollama_client import ask_llm


PLANNER_PROMPT = open(
    "llm/prompts/planner_prompt.txt"
).read()


def create_song_plan(expanded_prompt, genre="chillout"):
    """
    Creates a JSON song plan using Llama3, enforcing genre-specific track counts.
    """
    from core.style_config import STYLE_DATA
    style_info = STYLE_DATA.get(genre, STYLE_DATA["chillout"])
    genre_conf = style_info["pipeline"]
    
    min_t = genre_conf["min_tracks"]
    max_t = genre_conf["max_tracks"]
    min_b = genre_conf["min_bars"]
    max_b = genre_conf["max_bars"]
    
    # Get estimated BPM from style data ranges
    est_bpm = style_info["bpm_ranges"][0][0]

    enforcement = (
        f"\nOBLIGATORY DURATION CONTROL:\n"
        f"- Target Duration: 4:00 to 6:30 minutes.\n"
        f"- BPM: {est_bpm} (Estimated)\n"
        f"- Total Bars MUST be between {min_b} and {max_b} bars total.\n"
        f"- If you use fewer than {min_b} bars, the song will be too short. If you use more than {max_b}, it will be too long.\n"
        f"- Every section MUST describe at least {min_t} and at most {max_t} tracks."
    )

    final_prompt = (
        PLANNER_PROMPT +
        enforcement +
        "\n\n" +
        expanded_prompt
    )

    raw = ask_llm(final_prompt, temperature=0.8)

    if not raw:
        print("ERROR: LLM returned an empty response.", flush=True)
        return {}

    # Robust JSON extraction
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        # Fallback for generic code blocks
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
        else:
            raw = parts[0]
            
    # Remove any leading/trailing non-json characters (like conversational text)
    raw = raw.strip()
    if not (raw.startswith("{") or raw.startswith("[")):
        # Try to find the first '{' and last '}'
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start:end+1]

    # CLEANUP: Fix common LLM JSON errors before parsing
    import re
    
    # 1. Fix unquoted pitch ranges like [C1, C2] -> ["C1", "C2"]
    # This specifically targets arrays of characters and numbers that aren't quoted
    raw = re.sub(r'\[([A-G][b#]?[0-9]),\s*([A-G][b#]?[0-9])\]', r'["\1", "\2"]', raw)
    
    # 2. Fix trailing commas in arrays/objects
    raw = re.sub(r',\s*([\]}])', r'\1', raw)

    print(f"DEBUG: Final string for JSON parsing:\n{raw}\n", flush=True)

    try:
        plan = json.loads(raw)
        
        # Post-parsing fix for pitch_range (convert note names to MIDI numbers if they escaped the regex or were quoted)
        NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
        
        def note_to_midi(n):
            if isinstance(n, int): return n
            if not isinstance(n, str): return 60
            match = re.match(r"([A-G][b#]?)(-?[0-9])", n)
            if match:
                name, octave = match.groups()
                return (int(octave) + 1) * 12 + NOTE_MAP.get(name, 0)
            return 60

        for section in plan.get("sections", []):
            for track in section.get("tracks", []):
                pr = track.get("pitch_range", [36, 84])
                if isinstance(pr, list) and len(pr) == 2:
                    track["pitch_range"] = [note_to_midi(pr[0]), note_to_midi(pr[1])]
        
        title = plan.get("title", "untitled")
        print(f"SUCCESS: Plan created for '{title}'", flush=True)
        for s in plan.get("sections", []):
            print(f"  Section: {s.get('name')} | Bars: {s.get('bars')} | Transition: {s.get('transition')}", flush=True)
        return plan
    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: JSON decoding failed. Error: {e}", flush=True)
        print(f"Content that failed to parse: {raw}", flush=True)
        raise e
