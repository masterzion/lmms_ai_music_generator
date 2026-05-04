import pretty_midi
import numpy as np
from typing import List, Dict, Union, Any
from .schema import Composition, Track

class ScaleMapper:
    @staticmethod
    def get_midi_note(root_midi: int, degree: int, custom_intervals: List[int] = None) -> int:
        """
        Converts a root MIDI note, scale intervals, and degree to a final MIDI note number.
        """
        # Fallback if AI provides no intervals
        intervals = custom_intervals or [0, 2, 3, 5, 7, 8, 10]
        
        # Calculate note
        octave_offset = degree // len(intervals)
        degree_idx = degree % len(intervals)
        
        return root_midi + (octave_offset * 12) + intervals[degree_idx]

class SequencerEngine:
    def __init__(self, composition: Composition):
        self.comp = composition
        self.pm = pretty_midi.PrettyMIDI(initial_tempo=self.comp.meta.bpm)
        self.step_duration = 60.0 / self.comp.meta.bpm / 4.0  # 16th notes
        
    def _humanize_note(self, midi_note: int, start: float, duration: float, velocity: int) -> pretty_midi.Note:
        """Adds subtle timing and velocity variations + MIDI safety clamp."""
        # Safety Guard: Ensure note is in valid 0-127 range
        safe_note = max(0, min(127, int(midi_note)))
        
        offset = np.random.uniform(-0.005, 0.005) # +/- 5ms
        human_start = max(0, start + offset)
        human_vel = int(np.clip(velocity + np.random.randint(-10, 10), 1, 127))
        return pretty_midi.Note(human_vel, safe_note, human_start, human_start + duration)

    def generate(self) -> pretty_midi.PrettyMIDI:
        print(f"--- Starting MIDI Generation (BPM: {self.comp.meta.bpm}) ---")
        # Create tracks
        for name, track_data in self.comp.tracks.items():
            t_type = track_data.type.lower()
            print(f"Processing Track: [{name}] (Type: {t_type})")
            
            # ENHANCED ALIAS DETECTION
            is_drum = any(k in t_type for k in ["drum", "perc", "kick", "snare", "hat", "clap", "hit", "be"])
            is_mono = any(k in t_type for k in ["mono", "bass", "lead", "melodic", "arp", "seq"])
            is_poly = any(k in t_type for k in ["poly", "chord", "pad", "piano", "organ", "synth", "atmosphere", "string", "brass", "horn", "choir", "vocal", "orchestra", "texture", "cloud"])

            if is_drum:
                self._process_drum_track(name, track_data)
            elif is_mono:
                self._process_mono_track(name, track_data)
            elif is_poly:
                self._process_poly_track(name, track_data)
            else:
                # Default to poly if we can't tell (most flexible)
                print(f"Note: Defaulting unknown type '{t_type}' to polyphonic.")
                self._process_poly_track(name, track_data)
        
        print(f"Generation Complete. Total Tracks: {len(self.pm.instruments)}")
        
        # FINAL AUDIT REPORT
        print("\n--- FINAL PRODUCTION AUDIT ---")
        total_duration = self.pm.get_end_time()
        print(f"Total Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
        
        for inst in self.pm.instruments:
            note_count = len(inst.notes)
            status = " [ACTIVE]" if note_count > 0 else " [SILENT!]"
            print(f"Track: {inst.name:<20} | Notes: {note_count:>4} {status}")
        print("-------------------------------\n")
        
        return self.pm

    def _process_drum_track(self, name: str, track: Track):
        instrument = pretty_midi.Instrument(program=0, is_drum=True, name=name)
        
        current_time = 0.0
        drum_map = {"kick": 36, "snare": 38, "hat": 42, "clap": 39}
        
        if not track.patterns: return

        for idx, section_info in enumerate(self.comp.structure):
            # NEW: Schedule Check
            if track.schedule is not None and idx not in track.schedule:
                current_time += (section_info.bars * 16 * self.step_duration)
                continue

            pattern_name = section_info.section
            pattern = track.patterns.get(pattern_name) or list(track.patterns.values())[0]
            
            # Pattern is now a Dict[str, str]
            if not isinstance(pattern, dict): continue

            for bar in range(section_info.bars):
                for sound, midi_note in drum_map.items():
                    steps = pattern.get(sound, "-" * 16)
                    for i, step in enumerate(steps):
                        if step == "X":
                            start = current_time + (i * self.step_duration)
                            # Humanized note
                            note = self._humanize_note(midi_note, start, 0.1, 100)
                            instrument.notes.append(note)
                current_time += (16 * self.step_duration)
        
        self.pm.instruments.append(instrument)

    def _unwrap_pattern(self, pattern: Any) -> Any:
        """Robustly extracts a list or dict from an LLM-provided pattern object."""
        if isinstance(pattern, list): return pattern
        if isinstance(obj := pattern, dict):
            # If it's a dict, try to find the list/string inside
            for val in obj.values():
                if isinstance(val, (list, str)): return val
        return pattern

    def _process_mono_track(self, name: str, track: Track):
        instrument = pretty_midi.Instrument(program=38, name=name)
        
        current_time = 0.0
        root_midi = self.comp.meta.root_midi
        
        if not track.patterns: return

        for idx, section_info in enumerate(self.comp.structure):
            if track.schedule is not None and idx not in track.schedule:
                current_time += (section_info.bars * 16 * self.step_duration)
                continue

            pattern_name = section_info.section
            pattern = track.patterns.get(pattern_name) or list(track.patterns.values())[0]
            
            pattern = self._unwrap_pattern(pattern)
            if not isinstance(pattern, list): continue

            for bar in range(section_info.bars):
                for i, degree in enumerate(pattern):
                    if i >= 16: break
                    
                    # Case A: Integer scale degree
                    if isinstance(degree, int) and degree >= 0:
                        midi_note = ScaleMapper.get_midi_note(root_midi, degree, self.comp.meta.intervals)
                        start = current_time + (i * self.step_duration)
                        note = self._humanize_note(midi_note, start, self.step_duration * 0.9, 100)
                        instrument.notes.append(note)
                    
                    # Case B: Rhythmic string
                    elif isinstance(degree, str) and "X" in degree.upper():
                        for char_idx, char in enumerate(degree):
                            if char.upper() == "X":
                                midi_note = ScaleMapper.get_midi_note(root_midi, 0, self.comp.meta.intervals)
                                sub_step = self.step_duration / len(degree)
                                start = current_time + (i * self.step_duration) + (char_idx * sub_step)
                                note = self._humanize_note(midi_note, start, sub_step * 0.9, 100)
                                instrument.notes.append(note)
                
                current_time += (16 * self.step_duration)

        self.pm.instruments.append(instrument)

    def _process_poly_track(self, name: str, track: Track):
        instrument = pretty_midi.Instrument(program=0, name=name)
        
        current_time = 0.0
        root_midi = self.comp.meta.root_midi
 
        source = track.motifs if track.motifs else track.patterns
        if not source: return

        for idx, section_info in enumerate(self.comp.structure):
            if track.schedule is not None and idx not in track.schedule:
                current_time += (section_info.bars * 16 * self.step_duration)
                continue

            motif_name = section_info.section
            motif = source.get(motif_name) or list(source.values())[0]
            
            motif = self._unwrap_pattern(motif)
            if not isinstance(motif, list): continue

            for bar in range(section_info.bars):
                for i, degree in enumerate(motif):
                    if i >= 16: break
                    if degree == -1: continue

                    start = current_time + (i * self.step_duration)
                    degrees = degree if isinstance(degree, list) else [degree]
                    
                    if np.random.random() < (track.density or 0.6):
                        for d in degrees:
                            if d == -1: continue
                            
                            if isinstance(d, int) and d >= 0:
                                midi_note = ScaleMapper.get_midi_note(root_midi, d, self.comp.meta.intervals)
                                note = self._humanize_note(midi_note, start, self.step_duration * 2, 80)
                                instrument.notes.append(note)
                            
                            elif isinstance(d, str) and "X" in d.upper():
                                for char_idx, char in enumerate(d):
                                    if char.upper() == "X":
                                        midi_note = ScaleMapper.get_midi_note(root_midi, 0, self.comp.meta.intervals)
                                        sub_step = self.step_duration / len(d)
                                        s_start = start + (char_idx * sub_step)
                                        note = self._humanize_note(midi_note, s_start, sub_step * 2, 80)
                                        instrument.notes.append(note)
                
                current_time += (16 * self.step_duration)

        self.pm.instruments.append(instrument)
