import json
import requests
from typing import Optional, Dict, Any, List
from .schema import Composition

class Composer:
    def __init__(self, model_name: str = "llama3:8b", api_url: str = "http://192.168.2.188:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url
        self.system_prompt = """You are a professional music composition engine.
Output ONLY valid JSON. 

### FORMAT RULES:
1. DRUMS: Use a dictionary of 16-character strings. NO WRAPPERS. Example: {"kick": "X---", "snare": "----"}
2. MELODY/BASS: Use lists of 16 integers (scale degrees). 0=Root, -1=Rest.
3. ROOT: Must be a string like "A1", "C2", etc.
4. TOTAL LENGTH: Sum of 'bars' in 'structure' must be 140-176.

### GOOD EXAMPLE:
{
  "meta": {"bpm": 128, "scale": "A_minor", "swing": 0.0},
  "structure": [{"section": "A", "bars": 160}],
  "tracks": {
    "drums": {
      "type": "drum_machine",
      "patterns": {"A": {"kick": "X---", "snare": "----", "hat": "X-X-", "clap": "----"}}
    },
    "bass": {
      "type": "monophonic", "root": "A1", 
      "patterns": {"A": [0,0,0,0, 3,3,3,3, 5,5,5,5, 7,7,7,7]}
    }
  }
}

Output JSON only. No text before or after.
"""

    def get_ace_step_pattern(self, prompt: str, energy: float = 0.8) -> Optional[List[int]]:
        """Requests a MIDI pattern from the Steam Deck / ROCm remote bridge."""
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
                print("Bridge Handshake Successful. Downloading pattern...")
                # Load the MIDI file from the binary response stream
                midi_data = io.BytesIO(response.content)
                mid = mido.MidiFile(file=midi_data)
                
                # Extract pattern (reverse the 60+note logic from server)
                pattern = []
                for track in mid.tracks:
                    for msg in track:
                        if msg.type == 'note_on':
                            pattern.append(msg.note - 60)
                        elif msg.type == 'note_off' and msg.time > 0:
                            # Handle rests (if the time between notes is large)
                            rests = msg.time // 120 # 120 ticks = 16th note
                            pattern.extend([-1] * (rests - 1))
                
                print(f"Extracted {len(pattern)} notes from bridge MIDI.")
                # Ensure it's exactly the requested length (usually 16)
                return pattern[:16]
            else:
                print(f"Bridge Error: Status Code {response.status_code}")
        except Exception as e:
            print(f"Bridge connection failed (Offline?): {e}")
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
                return Composition(**data)
                
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
