import pretty_midi
import numpy as np
from typing import List, Dict, Union
from .schema import Composition, Track

class ScaleMapper:
    # Basic scale formulas (intervals from root)
    SCALES = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "chromatic": list(range(12))
    }

    NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    @staticmethod
    def get_midi_note(root_str: str, scale_name: str, degree: int) -> int:
        """
        Converts a root note (e.g. 'A2'), scale name ('minor'), and degree (0-based)
        to a MIDI note number.
        """
        # Parse root
        import re
        match = re.match(r"([A-G]#?)(\d+)", root_str)
        if not match:
            raise ValueError(f"Invalid root note format: {root_str}")
        
        note_name, octave = match.groups()
        root_val = ScaleMapper.NOTES.index(note_name) + (int(octave) + 1) * 12
        
        # Get scale intervals
        scale_type = scale_name.lower()
        if scale_type not in ScaleMapper.SCALES:
            scale_type = "minor" # Fallback
            
        intervals = ScaleMapper.SCALES[scale_type]
        
        # Calculate note
        octave_offset = degree // len(intervals)
        degree_idx = degree % len(intervals)
        
        return root_val + (octave_offset * 12) + intervals[degree_idx]

class SequencerEngine:
    def __init__(self, composition: Composition):
        self.comp = composition
        self.pm = pretty_midi.PrettyMIDI(initial_tempo=self.comp.meta.bpm)
        self.step_duration = 60.0 / self.comp.meta.bpm / 4.0  # 16th notes
        
    def _humanize_note(self, midi_note: int, start: float, duration: float, velocity: int) -> pretty_midi.Note:
        """Adds subtle timing and velocity variations."""
        offset = np.random.uniform(-0.005, 0.005) # +/- 5ms
        human_start = max(0, start + offset)
        human_vel = int(np.clip(velocity + np.random.randint(-10, 10), 1, 127))
        return pretty_midi.Note(human_vel, midi_note, human_start, human_start + duration)

    def generate(self) -> pretty_midi.PrettyMIDI:
        print(f"--- Starting MIDI Generation (BPM: {self.comp.meta.bpm}) ---")
        # Create tracks
        for name, track_data in self.comp.tracks.items():
            t_type = track_data.type.lower()
            print(f"Processing Track: [{name}] (Type: {t_type})")
            
            if t_type in ["drum_machine", "drums", "percussion"]:
                self._process_drum_track(name, track_data)
            elif t_type in ["monophonic", "mono", "bass", "lead", "melodic"]:
                self._process_mono_track(name, track_data)
            elif t_type in ["poly", "polyphonic", "chords", "pads", "piano"]:
                self._process_poly_track(name, track_data)
            else:
                print(f"Warning: Unknown track type '{t_type}'. Skipping.")
        
        print(f"Generation Complete. Total Tracks: {len(self.pm.instruments)}")
        return self.pm

    def _process_drum_track(self, name: str, track: Track):
        instrument = pretty_midi.Instrument(program=0, is_drum=True, name=name)
        
        current_time = 0.0
        drum_map = {"kick": 36, "snare": 38, "hat": 42, "clap": 39}
        
        if not track.patterns: return

        for section_info in self.comp.structure:
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

    def _process_mono_track(self, name: str, track: Track):
        instrument = pretty_midi.Instrument(program=38, name=name)
        
        current_time = 0.0
        root_note = track.root or "A1"
        scale_type = self.comp.meta.scale.split("_")[-1] if "_" in self.comp.meta.scale else "minor"
        
        if not track.patterns: return

        for section_info in self.comp.structure:
            pattern_name = section_info.section
            pattern = track.patterns.get(pattern_name) or list(track.patterns.values())[0]
            
            # Ensure it's a list of ints
            if not isinstance(pattern, list): continue

            for bar in range(section_info.bars):
                for i, degree in enumerate(pattern):
                    if i >= 16: break
                    if degree >= 0:
                        midi_note = ScaleMapper.get_midi_note(root_note, scale_type, degree)
                        start = current_time + (i * self.step_duration)
                        # Humanized note
                        note = self._humanize_note(midi_note, start, self.step_duration * 0.9, 100)
                        instrument.notes.append(note)
                current_time += (16 * self.step_duration)

        self.pm.instruments.append(instrument)

    def _process_poly_track(self, name: str, track: Track):
        instrument = pretty_midi.Instrument(program=0, name=name)
        
        current_time = 0.0
        root_note = f"C{track.octave or 4}"
        scale_type = self.comp.meta.scale.split("_")[-1] if "_" in self.comp.meta.scale else "minor"

        # Check both motifs and patterns for poly tracks
        source = track.motifs if track.motifs else track.patterns
        if not source: return

        for section_info in self.comp.structure:
            motif_name = section_info.section
            motif = source.get(motif_name) or list(source.values())[0]
            
            # Ensure we are dealing with a list
            if not isinstance(motif, list): continue

            for bar in range(section_info.bars):
                for i, degree in enumerate(motif):
                    if i >= 16: break
                    midi_note = ScaleMapper.get_midi_note(root_note, scale_type, degree)
                    start = current_time + (i * self.step_duration)
                    if np.random.random() < (track.density or 0.6):
                        # Humanized note
                        note = self._humanize_note(midi_note, start, self.step_duration * 2, 80)
                        instrument.notes.append(note)
                current_time += (16 * self.step_duration)

        self.pm.instruments.append(instrument)
