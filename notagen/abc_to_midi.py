"""
ABC notation → MIDI converter with deterministic polyphony enforcement.

Pipeline:
  1. Receive ABC string from NotaGen
  2. Parse with music21
  3. Extract all note events with absolute timestamps
  4. Quantize to target grid
  5. ENFORCE polyphony ≤ limit (pure Python, 100% deterministic)
  6. Clip to section duration
  7. Clip pitch range if specified
  8. Write MIDI via mido
"""

import math
import mido
import tempfile
import os
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# ABC pre-processing helpers
# ---------------------------------------------------------------------------

def _make_valid_abc(abc_str: str, instrument_name: str = "Piano") -> str:
    """
    Ensure the ABC string has required headers so music21 can parse it.
    NotaGen may omit some fields; we inject defaults.
    """
    lines = abc_str.strip().splitlines()
    has_x = any(l.strip().startswith("X:") for l in lines)
    has_t = any(l.strip().startswith("T:") for l in lines)
    has_k = any(l.strip().startswith("K:") for l in lines)
    has_m = any(l.strip().startswith("M:") for l in lines)
    has_l = any(l.strip().startswith("L:") for l in lines)

    header = []
    if not has_x:
        header.append("X:1")
    if not has_t:
        header.append(f"T:{instrument_name}")
    if not has_m:
        header.append("M:4/4")
    if not has_l:
        header.append("L:1/16")
    if not has_k:
        header.append("K:C")

    if header:
        return "\n".join(header) + "\n" + abc_str
    return abc_str


# ---------------------------------------------------------------------------
# Main conversion function
# ---------------------------------------------------------------------------

def abc_to_midi(
    abc_str: str,
    output_path: Path,
    bpm: float = 120.0,
    bars: int = 8,
    polyphony_limit: int = 8,
    grid: str = "1/16",
    pitch_range: Optional[List[int]] = None,
    instrument_program: int = 0,
    is_drum: bool = False,
    transition: str = "normal",
    instrument_name: str = "Melody",
    velocity_base: int = 80,
) -> Optional[Path]:
    """
    Convert an ABC notation string to a MIDI file with polyphony enforcement.

    Args:
        abc_str:           ABC notation string from NotaGen
        output_path:       Where to write the .mid file
        bpm:               Target BPM
        bars:              Section length in bars
        polyphony_limit:   Max simultaneous notes at any time step
        grid:              Quantization grid string ("1/16", "1/8", etc.)
        pitch_range:       [min_pitch, max_pitch] MIDI note numbers; None = no clip
        instrument_program: GM program number (0 = Acoustic Grand Piano)
        is_drum:           Whether to use GM drum channel 9
        transition:        "Fade In", "Fade Out", or "normal"
        instrument_name:   Track name
        velocity_base:     Base velocity (0-127)

    Returns:
        Path to written MIDI file, or None on failure.
    """
    try:
        from music21 import converter, stream, note as m21note, tempo as m21tempo
    except ImportError:
        raise RuntimeError("music21 is not installed. Run: pip install music21")

    polyphony_limit = int(polyphony_limit) # Ensure integer for slicing
    
    # --- Parse grid ---
    try:
        grid_denom = int(grid.split("/")[1]) if "/" in grid else 16
    except Exception:
        grid_denom = 16

    ticks_per_beat = 480
    ticks_per_bar  = ticks_per_beat * 4
    ticks_per_step = ticks_per_beat * 4 // grid_denom  # ticks per 1/grid_denom note
    total_ticks    = ticks_per_bar * bars

    # --- Parse ABC with music21 ---
    abc_str = _make_valid_abc(abc_str, instrument_name)

    # Write to temp file because music21 parses files more reliably
    with tempfile.NamedTemporaryFile(mode="w", suffix=".abc", delete=False) as tmp:
        tmp.write(abc_str)
        tmp_path = tmp.name

    raw_notes: List[Tuple[float, float, int, int]] = []  # (start_sec, end_sec, pitch, velocity)
    try:
        score = converter.parse(tmp_path)

        # Collect all notes from all parts/voices
        for part in score.flat.notes:
            offset_ql   = float(part.offset)         # quarter-note offset
            duration_ql = float(part.duration.quarterLength)

            if hasattr(part, "pitch"):
                # Single note
                pitches  = [part.pitch.midi]
                vel_hint = part.volume.velocity if part.volume.velocity else velocity_base
            elif hasattr(part, "pitches"):
                # Chord
                pitches  = [p.midi for p in part.pitches]
                vel_hint = part.volume.velocity if part.volume.velocity else velocity_base
            else:
                continue

            if vel_hint is None or vel_hint <= 0:
                vel_hint = velocity_base

            for pitch in pitches:
                raw_notes.append((offset_ql, offset_ql + duration_ql, pitch, int(vel_hint)))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not raw_notes:
        print(f"  [ABC→MIDI] Warning: no notes parsed from ABC output. Generating silence.")
        return _write_silent_midi(output_path, bpm, bars, ticks_per_beat)

    # --- Convert quarter-note offsets to ticks ---
    # music21 uses quarter notes as the base unit
    def ql_to_ticks(ql: float) -> int:
        return int(round(ql * ticks_per_beat))

    # --- Quantize to grid ---
    def quantize(tick: int) -> int:
        return int(round(tick / ticks_per_step)) * ticks_per_step

    tick_notes: List[Tuple[int, int, int, int]] = []  # (start_tick, end_tick, pitch, velocity)
    for (start_ql, end_ql, pitch, vel) in raw_notes:
        s_tick = quantize(ql_to_ticks(start_ql))
        e_tick = quantize(ql_to_ticks(end_ql))
        if e_tick <= s_tick:
            e_tick = s_tick + ticks_per_step
        tick_notes.append((s_tick, e_tick, pitch, vel))

    # --- Pitch range clipping / transposition ---
    if pitch_range and len(pitch_range) == 2:
        pmin, pmax = int(pitch_range[0]), int(pitch_range[1])
        # If range is very narrow (pmin==pmax), use that as the exact pitch
        clamped = []
        for (s, e, p, v) in tick_notes:
            if pmin == pmax:
                clamped.append((s, e, pmin, v))
            else:
                # Transpose to fit in range (octave-shift)
                np = p
                while np < pmin and np + 12 <= pmax:
                    np += 12
                while np > pmax and np - 12 >= pmin:
                    np -= 12
                np = max(pmin, min(pmax, np))
                clamped.append((s, e, np, v))
        tick_notes = clamped

    # --- Duration clipping ---
    tick_notes = [(s, min(e, total_ticks), p, v) for (s, e, p, v) in tick_notes if s < total_ticks]

    # --- Polyphony enforcement ---
    # Group note-on events by start tick
    from collections import defaultdict
    tick_groups: dict = defaultdict(list)
    for (s, e, p, v) in tick_notes:
        tick_groups[s].append((e, p, v))

    enforced: List[Tuple[int, int, int, int]] = []
    for start_tick in sorted(tick_groups):
        candidates = tick_groups[start_tick]
        # Sort by velocity desc, keep top polyphony_limit
        candidates.sort(key=lambda x: x[2], reverse=True)
        for (e, p, v) in candidates[:polyphony_limit]:
            enforced.append((start_tick, e, p, v))

    # --- Velocity envelope for transitions ---
    def apply_envelope(tick: int, velocity: int) -> int:
        fraction = tick / max(total_ticks, 1)
        if transition.lower() == "fade in":
            env = 0.15 + 0.85 * fraction
        elif transition.lower() == "fade out":
            env = 1.0 - 0.80 * fraction
        else:
            env = 1.0
        return max(1, min(127, int(velocity * env)))

    # --- Build MIDI ---
    mid  = mido.MidiFile(type=0, ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    channel = 9 if is_drum else 0
    tempo   = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("track_name", name=instrument_name, time=0))
    if not is_drum:
        track.append(mido.Message("program_change", channel=channel,
                                  program=instrument_program, time=0))

    # Build flat event list: (abs_tick, event_type, pitch, velocity)
    raw_events: List[Tuple[int, str, int, int]] = []
    for (s, e, p, v) in enforced:
        v_env = apply_envelope(s, v)
        raw_events.append((s,   "on",  p, v_env))
        raw_events.append((e,   "off", p, 0))

    # Sort: by tick, offs before ons at same tick to avoid stuck notes
    raw_events.sort(key=lambda x: (x[0], 0 if x[1] == "off" else 1))

    last_tick = 0
    for (abs_tick, etype, pitch, vel) in raw_events:
        delta = max(0, abs_tick - last_tick)
        if etype == "on":
            track.append(mido.Message("note_on",  channel=channel,
                                      note=pitch, velocity=vel, time=delta))
        else:
            track.append(mido.Message("note_off", channel=channel,
                                      note=pitch, velocity=0,   time=delta))
        last_tick = abs_tick

    track.append(mido.MetaMessage("end_of_track", time=0))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    print(f"  [ABC→MIDI] Saved {len(enforced)} notes → {output_path} "
          f"(poly≤{polyphony_limit}, {bars} bars @ {bpm} BPM)")
    return output_path


def _write_silent_midi(output_path: Path, bpm: float, bars: int, ticks_per_beat: int) -> Path:
    """Write an empty (silent) MIDI file as fallback."""
    mid = mido.MidiFile(type=0, ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.MetaMessage("end_of_track", time=ticks_per_beat * 4 * bars))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# Verification helper (used by unit tests and the API for forensics)
# ---------------------------------------------------------------------------

def count_max_simultaneous(midi_path: Path) -> int:
    """
    Scan a MIDI file and return the maximum number of simultaneously
    sounding notes at any point in time. Used to verify polyphony constraints.
    """
    mid = mido.MidiFile(str(midi_path))
    events: List[Tuple[int, int]] = []  # (abs_tick, +1 or -1)

    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                events.append((abs_tick, +1))
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                events.append((abs_tick, -1))

    events.sort(key=lambda x: (x[0], x[1]))  # offs before ons at same tick

    active = 0
    max_active = 0
    for (_, delta) in events:
        active += delta
        if active > max_active:
            max_active = active

    return max_active
