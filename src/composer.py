import json
import requests
from typing import Optional, Dict, Any, List
from .schema import Composition

class Composer:
    def __init__(self, model_name: str = "llama3:8b", api_url: str = "http://192.168.2.188:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url
        self.system_prompt = """You are a Master Music Producer and Creative Director.
Output ONLY valid JSON. 

### YOUR TASK:
Translate "Style + Theme" into a professional music specification.
1. STYLE RESEARCH: Decide BPM and Scale.
2. TRACK COUNT: Pick a RANDOM number in genre range.
3. LIBRARIAN: Generate a 'title' and a 'folder' path (e.g., "ebm/war", "futurepop/science").
   Look at existing folders for inspiration, or create a new one if needed.
4. SCHEDULE: Create a dynamic arrangement [0, 1, 2...].

### FORMAT:
- META: bpm, scale, genre, title, folder, swing.
- Use LOWERCASE for all keys. NO LETTERS for patterns.

### GOOD EXAMPLE:
{
  "meta": {"bpm": 126, "scale": "D_phrygian", "genre": "EBM", "swing": 0.0},
  "structure": [{"section": "Intro", "bars": 8}, {"section": "Drop", "bars": 16}],
  "tracks": {
    "War_Drum": {"type": "drum_machine", "schedule": [0, 1], "patterns": {"Intro": {"kick": "X---"}}},
    "Alarm_Synth": {"type": "monophonic", "schedule": [1], "patterns": {"Drop": [0, 1, 0, 1]}}
  }
}
"""

    def get_ace_step_pattern(self, prompt: str, energy: float = 0.8) -> Optional[Dict[str, Any]]:
        """Requests a MIDI pattern and a Start/Stop schedule from the Steam Deck bridge."""
        import mido
        import io
        bridge_url = self.api_url.replace(":11434/api/generate", ":8000/generate_pattern")
        print(f"Handshaking with Steam Deck Bridge at {bridge_url}...")
        try:
            response = requests.post(
                bridge_url,
                json={"prompt": prompt, "energy": energy},
                timeout=14400,
                stream=True
            )
            if response.status_code == 200:
                print("Bridge Handshake Successful. Downloading pattern and schedule...")
                
                # Extract schedule from header
                schedule_raw = response.headers.get("X-Schedule", "")
                schedule = [int(x) for x in schedule_raw.split(",") if x.strip()]
                
                # Load the MIDI file
                midi_data = io.BytesIO(response.content)
                mid = mido.MidiFile(file=midi_data)
                
                pattern = []
                for track in mid.tracks:
                    for msg in track:
                        if msg.type == 'note_on':
                            pattern.append(msg.note - 60)
                        elif msg.type == 'note_off' and msg.time > 0:
                            rests = msg.time // 120
                            pattern.extend([-1] * (rests - 1))
                
                print(f"Extracted {len(pattern)} notes. Schedule: {schedule}")
                return {"pattern": pattern[:16], "schedule": schedule}
            else:
                print(f"Bridge Error: Status Code {response.status_code}")
        except Exception as e:
            print(f"Bridge connection failed: {e}")
            return None
        return None

    def compose(self, user_request: str, max_retries: int = 3) -> Composition:
        current_prompt = f"{self.system_prompt}\n\nUser Request: {user_request}\n\nJSON Output:"
        
        for attempt in range(max_retries):
            try:
                print(f"LLM Attempt {attempt + 1}...")
                response = requests.post(
                    self.api_url,
                    json={
                        "model": self.model_name,
                        "prompt": current_prompt,
                        "stream": False
                        # "format": "json" (Removed for better reasoning)
                    },
                    timeout=14400
                )
                response.raise_for_status()
                raw_content = response.json().get("response", "").strip()
                
                # Extract JSON if LLM added surrounding text
                if "{" in raw_content:
                    raw_json = raw_content[raw_content.find("{"):raw_content.rfind("}")+1]
                else:
                    raw_json = raw_content

                print(f"DEBUG: RAW LLM Output (first 100 chars): {raw_json[:100]}...")
                
                # Parse and validate
                data = json.loads(raw_json)
                
                # RECURSIVE LOWERCASE (Robustness for capitalized keys)
                def lowercase_keys(obj):
                    if isinstance(obj, dict):
                        return {k.lower(): lowercase_keys(v) for k, v in obj.items()}
                    if isinstance(obj, list):
                        return [lowercase_keys(i) for i in obj]
                    return obj
                
                data = lowercase_keys(data)
                comp = Composition(**data)

                # POST-PROCESS: Get schedules from Bridge for each track
                print("--- Refining Arrangement via Bridge ---")
                for name, track in comp.tracks.items():
                    bridge_data = self.get_ace_step_pattern(name, energy=track.density or 0.6)
                    if bridge_data:
                        # Use the Bridge pattern if track pattern is missing or for higher quality
                        pattern_name = list(track.patterns.keys())[0] if track.patterns else "A"
                        if not track.patterns: track.patterns = {}
                        track.patterns[pattern_name] = bridge_data["pattern"]
                        # Apply the Start/Stop schedule
                        track.schedule = bridge_data["schedule"]
                
                return comp
                
            except Exception as e:
                error_msg = str(e)
                print(f"Validation Error on attempt {attempt + 1}: {error_msg}")
                if attempt < max_retries - 1:
                    # Feed the error back to the LLM for the next attempt
                    current_prompt = f"The previous JSON was invalid. Error: {error_msg}\nPlease fix it and provide the full corrected JSON."
                else:
                    raise Exception(f"Failed after {max_retries} attempts. Last error: {error_msg}")

    def validate_and_fix(self, raw_data: Dict[str, Any]) -> Composition:
        """
        Takes raw dict data and tries to cast it to Composition.
        If it fails, this is where the 'Refinement Loop' would live.
        """
        try:
            return Composition(**raw_data)
        except Exception as e:
            print(f"Validation failed: {e}")
            # Potential for "Fix this JSON" prompt here
            raise
