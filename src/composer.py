import os
import json
import requests
from typing import Optional, Dict, Any, List
from .schema import Composition, Track

class Composer:
    def __init__(self, model_name: str = "llama3:8b", api_url: str = "http://192.168.2.188:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url
        self.system_prompt = """You are a Master Music Producer and Creative Director.
Output ONLY valid JSON. 

### YOUR TASK:
Translate "Style + Theme" into a professional music specification.
1. STYLE RESEARCH: Decide BPM and Scale.
2. TRACK COUNT: MANDATORY MINIMUM 10 TRACKS. 
3. DURATION: MANDATORY MINIMUM 4 MINUTES (total bars must sum to 140-160+).
4. LIBRARIAN: Generate 'title' and 'folder' (e.g., "ebm/war").
5. SCHEDULE: Create a dynamic arrangement [0, 1, 2...].

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

    def get_ace_step_pattern(self, prompt: str, theory: Dict[str, Any], energy: float = 0.8) -> Optional[Dict[str, Any]]:
        """Requests a MIDI pattern and a Start/Stop schedule from the Steam Deck bridge."""
        import mido
        import io
        bridge_url = self.api_url.replace(":11434/api/generate", ":8000/generate_pattern")
        print(f"Handshaking with Steam Deck Bridge at {bridge_url}...")
        try:
            response = requests.post(
                bridge_url,
                json={
                    "prompt": prompt, 
                    "energy": energy,
                    "genre": theory.get("genre", "Electronic"),
                    "root_midi": theory.get("root_midi", 48),
                    "intervals": theory["intervals"]
                },
                timeout=300,
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

    def validate_composition(self, comp: Composition) -> List[str]:
        """Validates that the composition meets the 10-track and 4-minute minimums."""
        errors = []
        # Check track count
        if len(comp.tracks) < 10:
            errors.append(f"Incomplete: Found only {len(comp.tracks)} tracks (Minimum 10 required).")
        
        # Check duration
        total_bars = sum(s.bars for s in comp.structure)
        duration_mins = (total_bars * 4) / comp.meta.bpm
        if duration_mins < 4.0:
            errors.append(f"Too short: Duration is {duration_mins:.2f} mins (Minimum 4.0 minutes required).")
            
        return errors

    def _extract_json(self, text: str) -> str:
        """Utility to pull JSON block from LLM verbosity."""
        if "{" in text:
            return text[text.find("{"):text.rfind("}")+1]
        return text

    def get_ace_step_theory(self, concept: str) -> Dict[str, Any]:
        """Ultimate Fallback: Requests entire music theory from ACE-Step bridge."""
        bridge_url = self.api_url.replace(":11434/api/generate", ":8000/research_theory")
        print(f"--- SUPREME FALLBACK: Requesting Theory from ACE-Step Bridge ---")
        try:
            response = requests.post(
                bridge_url,
                json={"prompt": concept, "system_prompt": self.system_prompt},
                timeout=14400
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Supreme Fallback failed: {e}")
        
        # Dead-end fallback
        return {
            "bpm": 120, "scale": "minor", "intervals": [0], 
            "root_midi": 48, "genre_notes": "Electronic", 
            "title": f"Production_{concept[:10]}", "folder": "misc"
        }

    def _research_theory(self, concept: str) -> Dict[str, Any]:
        """Stage 1: Ask the AI for music theory suggestions with 5x retry logic."""
        print(f"--- Stage 1: Musicology Research for '{concept}' ---")
        prompt = f"""Given "{concept}", suggest professional music theory parameters.
        Return ONLY valid JSON:
        {{
          "bpm": 128, 
          "scale": "phrygian", 
          "intervals": [0, 1, 3, 5, 7, 8, 10], 
          "root_midi": 48, 
          "genre_notes": "Dark industrial vibe.",
          "title": "Neon_Circuit",
          "folder": "futurepop/science"
        }}
        """
        for attempt in range(5):
            try:
                print(f"   Theory Attempt {attempt + 1}/5...")
                response = requests.post(
                    self.api_url,
                    json={"model": self.model_name, "prompt": prompt, "stream": False},
                    timeout=14400
                )
                raw_content = response.json().get("response", "")
                raw = self._extract_json(raw_content)
                data = json.loads(raw)
                
                # Basic validation: ensure keys exist
                required = ["bpm", "scale", "intervals", "root_midi", "genre_notes"]
                if all(k in data for k in required):
                    return data
                else:
                    print(f"      ! Missing keys in JSON. Retrying...")
                    print(data)
            except Exception as e:
                print(f"      ! Theory attempt {attempt + 1} failed: {e}")
        
        print(f"CRITICAL: Standard Research failed. Delegating to ACE-Step...")
        return self.get_ace_step_theory(concept)

    def _create_blueprint(self, concept: str, theory: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Design the structure and track list with 5x retry logic."""
        print(f"--- Stage 2: Designing Song Blueprint ---")
        prompt = f"""Given "{concept}" and theory {theory}, design a song BLUEPRINT.
        Requirements:
        1. MANDATORY: 10-12 instruments.
        2. MANDATORY: Total bars must be ~160 (to reach 4-5 minutes).
        Return ONLY valid JSON:
        {{
          "structure": [{{"section": "Intro", "bars": 32}}, {{"section": "Main", "bars": 64}}],
          "track_names": ["Drums", "Bass", "Synth_Pad", "Lead", "Atmosphere", "Fx", "Perc", "Sub", "Arp", "Hook"]
        }}
        """
        for attempt in range(5):
            try:
                print(f"   Blueprint Attempt {attempt + 1}/5...")
                response = requests.post(
                    self.api_url,
                    json={"model": self.model_name, "prompt": prompt, "stream": False},
                    timeout=14400
                )
                raw = self._extract_json(response.json().get("response", ""))
                data = json.loads(raw)
                
                # Validation: 10+ tracks and 140+ bars
                total_bars = sum(s["bars"] for s in data.get("structure", []))
                track_count = len(data.get("track_names", []))
                
                if track_count >= 10 and total_bars >= 140:
                    return data
                else:
                    print(f"      ! Blueprint failed validation: {track_count} tracks, {total_bars} bars. Retrying...")
            except Exception as e:
                print(f"      ! Blueprint attempt {attempt + 1} failed: {e}")
        
        print(f"CRITICAL: Blueprint design failed after 5 attempts. Using emergency recovery.")
        return {
            "structure": [{"section": "Main", "bars": 160}],
            "track_names": [f"Track_{i}" for i in range(10)]
        }

    def _generate_track(self, name: str, blueprint: Dict[str, Any], theory: Dict[str, Any]) -> Track:
        """Stage 3: Generate patterns for a single instrument."""
        print(f"   > Recording Track: [{name}]...")
        sections = [s["section"] for s in blueprint["structure"]]
        prompt = f"""Write MIDI patterns for the track "{name}".
        Song Structure: {blueprint['structure']}.
        Theme: {theory.get('genre_notes')}. Root MIDI: {theory.get('root_midi')}.
        Return ONLY JSON for one track. 
        MANDATORY: Provide a pattern for EVERY section listed in the structure.
        {{
          "type": "drum_machine" or "monophonic" or "polyphonic",
          "density": 0.7,
          "patterns": {{ 
             "{sections[0]}": [0, 1, 0, 1],
             "Next_Section": [0, 1, 2, 3]
          }}
        }}
        """
        try:
            response = requests.post(
                self.api_url,
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=14400
            )
            raw = self._extract_json(response.json().get("response", ""))
            data = json.loads(raw)
            return Track(**data)
        except Exception as e:
            print(f"      ! Track [{name}] failed: {e}. Using silent placeholder.")
            return Track(type="polyphonic", patterns={sections[0]: [0]})

    def _get_checkpoint_path(self, concept: str, stage: str) -> str:
        safe_concept = "".join([c if c.isalnum() else "_" for c in concept])[:50]
        os.makedirs("checkpoints", exist_ok=True)
        return f"checkpoints/{safe_concept}_{stage}.json"

    def _save_checkpoint(self, concept: str, stage: str, data: Any):
        path = self._get_checkpoint_path(concept, stage)
        with open(path, "w") as f:
            if hasattr(data, "dict"): # For Pydantic models
                json.dump(data.dict(), f, indent=2)
            else:
                json.dump(data, f, indent=2)
        print(f"   [Checkpoint Saved] -> {stage}")

    def _load_checkpoint(self, concept: str, stage: str) -> Optional[Any]:
        path = self._get_checkpoint_path(concept, stage)
        if os.path.exists(path):
            with open(path, "r") as f:
                print(f"   [Checkpoint Loaded] -> {stage}")
                return json.load(f)
        return None

    def compose(self, user_request: str, context: str = "", max_retries: int = 3) -> Composition:
        # Combined prompt for the AI, but 'user_request' remains the checkpoint key
        full_concept = f"{user_request}. {context}"
        
        # STEP 1: RESEARCH
        theory = self._load_checkpoint(user_request, "theory")
        if not theory:
            theory = self._research_theory(full_concept)
            self._save_checkpoint(user_request, "theory", theory)
        
        print(f"Theory: {theory.get('bpm')} BPM, Root {theory.get('root_midi')}")

        # STEP 2: BLUEPRINT
        blueprint = self._load_checkpoint(user_request, "blueprint")
        if not blueprint:
            blueprint = self._create_blueprint(full_concept, theory)
            self._save_checkpoint(user_request, "blueprint", blueprint)
            
        print(f"Blueprint: {len(blueprint['track_names'])} instruments, {sum(s['bars'] for s in blueprint['structure'])} total bars.")

    def _orchestrate_all_tracks(self, concept: str, blueprint: Dict[str, Any], theory: Dict[str, Any]) -> Dict[str, Track]:
        """Stage 3: Orchestrate all instruments in the blueprint."""
        print(f"--- Stage 3: Orchestrating All Instruments ---")
        tracks = {}
        for name in blueprint["track_names"]:
            # Check if this specific track is already done
            track_data = self._load_checkpoint(concept, f"track_{name}")
            if track_data:
                print(f"   > Track [{name}] found in checkpoint. Resuming...")
                tracks[name] = Track(**track_data)
                continue

            print(f"   > Orchestrating Track: [{name}]...")
            
            # 1. ACE-Step Bridge Handshake
            bridge_data = self.get_ace_step_pattern(name, theory, energy=0.7)
            if bridge_data:
                print(f"      + ACE-Step generated professional patterns and schedule.")
                track = Track(
                    type="polyphonic",
                    density=0.7,
                    patterns={s["section"]: bridge_data["pattern"] for s in blueprint["structure"]},
                    schedule=bridge_data["schedule"]
                )
            else:
                # 2. Internal Motif Fallback
                print(f"      ! Bridge unavailable. Using Internal Motif Sequencer...")
                import random
                is_drum = any(k in name.lower() for k in ["drum", "kick", "perc", "808", "snare", "hat"])
                
                if is_drum:
                    drum_notes = [36, 38, 42]
                    motif = [random.choice(drum_notes) if random.random() < 0.6 else -1 for _ in range(8)]
                else:
                    motif = [random.choice(theory["intervals"]) if random.random() < 0.6 else -1 for _ in range(8)]
                
                track = Track(
                    type="polyphonic",
                    density=0.6,
                    patterns={s["section"]: [motif[i % 8] for i in range(16)] for s in blueprint["structure"]},
                    schedule=None
                )

            self._save_checkpoint(concept, f"track_{name}", track)
            tracks[name] = track
        return tracks

    def compose(self, user_request: str, context: str = "", max_retries: int = 3) -> Composition:
        # Combined prompt for the AI
        full_concept = f"{user_request}. {context}"
        
        # STEP 1: RESEARCH
        theory = self._load_checkpoint(user_request, "theory")
        if not theory:
            theory = self._research_theory(full_concept)
            self._save_checkpoint(user_request, "theory", theory)
        
        print(f"Theory: {theory.get('bpm')} BPM, Root {theory.get('root_midi')}")

        # STEP 2: BLUEPRINT
        blueprint = self._load_checkpoint(user_request, "blueprint")
        if not blueprint:
            blueprint = self._create_blueprint(full_concept, theory)
            self._save_checkpoint(user_request, "blueprint", blueprint)
            
        print(f"Blueprint: {len(blueprint['track_names'])} instruments, {sum(s['bars'] for s in blueprint['structure'])} total bars.")

        # STEP 3: ORCHESTRATION
        tracks = self._orchestrate_all_tracks(user_request, blueprint, theory)

        # STEP 4: ASSEMBLE
        comp = Composition(
            meta={
                "bpm": theory["bpm"],
                "scale": theory["scale"],
                "intervals": theory["intervals"],
                "root_midi": theory["root_midi"],
                "genre": theory["genre_notes"],
                "title": theory.get("title", f"Production_{user_request[:10]}"),
                "folder": theory.get("folder", theory["genre_notes"].split()[0].lower())
            },
            structure=blueprint["structure"],
            tracks=tracks
        )

        # FINAL QC
        qc_errors = self.validate_composition(comp)
        if qc_errors:
            print(f"QC WARNING: {', '.join(qc_errors)}")

        return comp

    def validate_and_fix(self, raw_data: Dict[str, Any]) -> Composition:
        """
        Takes raw dict data and tries to cast it to Composition.
        If it fails, this is where the 'Refinement Loop' would live.
        """
        try:
            return Composition(**raw_data)
        except Exception as e:
            print(f"Validation failed: {e}")
            raise

    def compose_monolithic(self, user_request: str) -> Composition:
        """EXPERIMENTAL: Generate the entire composition in ONE handshake with a Master Prompt."""
        print(f"--- MONOLITHIC MODE: Delegating entire song to ACE-Step ---")
        bridge_url = "http://192.168.2.188:8000/generate_full_composition"
        
        # Build the Ultimate Professional Master Prompt
        master_prompt = f"""
        PRODUCE A HIGH-FIDELITY, PROFESSIONAL-GRADE MASTER COMPOSITION FOR: "{user_request}"
        
        You are an elite, multi-platinum EDM/Industrial music producer and audio engineer. 
        Your goal is to orchestrate a pristine, club-ready, dynamic track that rivals top-tier professional releases.
        
        FOUNDATIONAL STUDIO RULES:
        1. DURATION: Minimum 4 minutes of evolving, hypnotic arrangement.
        2. ORCHESTRATION: Minimum 10 distinct instruments. All must be ACTIVE (No silent tracks). MANDATORY: Every single instrument MUST generate notes. 0-note tracks are STRICTLY FORBIDDEN.
        
        RHYTHM & GROOVE MECHANICS:
        3. PERCUSSION: MANDATORY dedicated 'Beat' (Kicks/Snares) and 'Industrial_Claps' tracks.
        4. FOUNDATION: FORCE a relentlessly driving, quantized beat foundation. The groove must lock the listener in.
        5. SYNCOPATION: Implement off-beat hi-hats and syncopated percussion hits to create complex rhythmic pockets.
        
        ARRANGEMENT & DYNAMICS:
        6. TRACK PRESENCE (MANDATORY): You must feature at least 3 core baseline instruments. The Sub-Bass, Beat, and Industrial_Claps tracks MUST be active for at least 90% of the song. All other secondary instruments MUST be active for at least 40% of the song.
        7. TENSION & RELEASE: Masterful use of energy. Build massive tension using Risers and fast arpeggios. Release the tension into devastating, high-energy drops where the Sub-Bass and Kick hit with maximum impact.
        8. STAGGERED ENTRIES: Do not start all instruments at once. Introduce elements sequentially (Intro -> Build -> Drop -> Breakdown -> Climax -> Outro).
        9. CADENCE (CALL-AND-RESPONSE): ALTERNATE the rhythmic phrasing between lead synths and basslines (create dynamic space, avoid mud).
        
        FREQUENCY SPREAD & SOUND DESIGN:
        9. THE LOW END: Ensure the Sub-Bass is strictly isolated in the lowest octaves. It must pulse with the Kick.
        10. THE MID-RANGE: Use rich, wide Chord Pads and driving Acid Lines to fill the spectrum without clashing.
        11. THE HIGH END: Crystal clear Leads, aggressive Vox Effects, and sharp metallic percussions piercing the top frequencies.
        
        EXECUTE THE VISION. Output ONLY the meticulously structured JSON.
        """
        
        try:
            response = requests.post(
                bridge_url,
                json={"prompt": master_prompt, "system_prompt": self.system_prompt},
                timeout=14400
            )
            data = response.json()
            return Composition(**data)
        except Exception as e:
            print(f"Monolithic composition failed: {e}")
            raise

    def render_to_audio(self, midi_path: str):
        """Sends the MIDI to the Steam Deck for FluidSynth rendering."""
        print(f"--- RENDERER: Sending {os.path.basename(midi_path)} to Steam Deck ---")
        bridge_url = "http://192.168.2.188:8000/render_wav"
        
        try:
            with open(midi_path, "rb") as f:
                files = {"file": (os.path.basename(midi_path), f, "audio/midi")}
                response = requests.post(bridge_url, files=files, timeout=600)
            
            if response.status_code == 200:
                out_path = midi_path.replace(".mid", ".wav")
                with open(out_path, "wb") as f:
                    f.write(response.content)
                print(f"--- SUCCESS: Remote rendering complete. Saved to: {out_path} ---")
                return True
            else:
                error_detail = response.json().get("detail", response.text)
                print(f"Server rejected rendering: {error_detail}")
                raise Exception(error_detail)
                
        except Exception as e:
            print(f"Failed to connect to rendering bridge: {e}")
            raise e
