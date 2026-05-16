"""
Rule-based drum/percussion MIDI generator.

Generates rhythmic patterns deterministically — NO LLM involved.
Guaranteed polyphony = 1 (one note per time slot), so hardware
constraints are satisfied 100% of the time.

General MIDI percussion note numbers (channel 10):
  35 = Acoustic Bass Drum
  36 = Bass Drum 1
  38 = Acoustic Snare
  39 = Hand Clap
  40 = Electric Snare
  42 = Closed Hi-Hat
  44 = Pedal Hi-Hat
  46 = Open Hi-Hat
  49 = Crash Cymbal 1
  51 = Ride Cymbal 1
"""

import mido
import math
from pathlib import Path
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# Rhythmic templates:  list of (grid_step_index, velocity_fraction)
# Grid step 0 = beat 1, step N = N*(1/grid_resolution) into the bar.
# ---------------------------------------------------------------------------

# 4/4 bar with 1/16 resolution → 16 steps per bar
TEMPLATES = {
    # clap / snare — beats 2 and 4
    "clap_basic": [(4, 0.85), (12, 0.85)],
    # clap snappy — 2+4 with light syncopation
    "clap_snappy": [(4, 0.9), (6, 0.55), (12, 0.9), (14, 0.55)],
    # clap funky dense
    "clap_dense": [(2, 0.6), (4, 0.9), (6, 0.55), (10, 0.6), (12, 0.9), (14, 0.6)],
    # hi-hat eight notes
    "hihat_eighth": [(0,0.7),(2,0.6),(4,0.7),(6,0.6),(8,0.7),(10,0.6),(12,0.7),(14,0.6)],
    # hi-hat 16th dense
    "hihat_16th": [(i, 0.7 if i % 4 == 0 else 0.55) for i in range(16)],
    # kick four on the floor
    "kick_4floor": [(0, 0.95), (4, 0.95), (8, 0.95), (12, 0.95)],
    # kick house offbeat
    "kick_house":  [(0, 0.95), (4, 0.95), (6, 0.5), (8, 0.95), (12, 0.95), (14, 0.5)],
    # snare typical
    "snare_basic": [(4, 0.88), (12, 0.88)],
    # snare rimshot ghost
    "snare_ghost": [(4,0.9),(7,0.45),(12,0.9),(15,0.45)],
    # sparse single hit (fallback)
    "sparse":      [(0, 0.7)],
}

# Map style keywords → template names
STYLE_MAP = {
    "clap":   ["clap_snappy", "clap_basic", "clap_dense"],
    "snap":   ["clap_snappy", "clap_basic"],
    "snare":  ["snare_basic", "snare_ghost"],
    "rimshot":["snare_ghost"],
    "hihat":  ["hihat_eighth", "hihat_16th"],
    "hat":    ["hihat_eighth"],
    "kick":   ["kick_4floor", "kick_house"],
    "bass drum": ["kick_4floor"],
    "cymbal": ["hihat_eighth"],
}

# Map style keyword → GM note pitch
PITCH_MAP = {
    "clap":   39,
    "snap":   39,
    "snare":  38,
    "rimshot":37,
    "hihat":  42,
    "hat":    42,
    "open hat": 46,
    "kick":   36,
    "bass drum": 36,
    "cymbal": 49,
}


def _pick_template(style_desc: str, density: float) -> Tuple[str, int]:
    """
    Choose the best template name and GM pitch from a style description.
    Returns (template_key, gm_pitch).
    """
    style_lower = style_desc.lower()

    # Find pitch
    pitch = 39  # default: hand clap
    for kw, p in PITCH_MAP.items():
        if kw in style_lower:
            pitch = p
            break

    # Find template
    for kw, tmpl_list in STYLE_MAP.items():
        if kw in style_lower:
            # Choose denser or sparser template based on density
            idx = min(int(density * len(tmpl_list)), len(tmpl_list) - 1)
            return tmpl_list[idx], pitch

    # Fallback based on density
    if density > 0.6:
        return "clap_dense", pitch
    return "clap_basic", pitch


def generate(
    style_desc: str,
    density: float,
    grid: str,
    bars: int,
    bpm: float,
    polyphony_limit: int = 1,
    transition: str = "normal",
    pitch_range: Optional[List[int]] = None,
    output_path: Optional[Path] = None,
    velocity_base: int = 100,
) -> mido.MidiFile:
    """
    Generate a drum/percussion MIDI pattern.

    Args:
        style_desc:    Natural language description e.g. "Snappy clap pattern"
        density:       0.0 – 1.0, rhythmic density
        grid:          Time grid string e.g. "1/16", "1/8"
        bars:          Number of bars to generate
        bpm:           Tempo in beats per minute
        polyphony_limit: Max simultaneous notes (always enforced; typically 1)
        transition:    "Fade In", "Fade Out", or "normal"
        pitch_range:   Not used for drums; GM pitch is determined by style
        output_path:   If given, save MIDI to this path

    Returns:
        mido.MidiFile with the pattern
    """
    # --- Parse grid resolution ---
    try:
        grid_parts = grid.split("/")
        grid_denom = int(grid_parts[1]) if len(grid_parts) > 1 else 16
    except Exception:
        grid_denom = 16

    # Steps per bar (assuming 4/4)
    steps_per_bar = grid_denom  # e.g. 16 steps/bar for 1/16

    # MIDI ticks per beat (standard)
    ticks_per_beat = 480
    ticks_per_step = ticks_per_beat * 4 // steps_per_bar  # 4 beats per bar

    # --- Pick template ---
    template_key, gm_pitch = _pick_template(style_desc, density)
    template_steps = TEMPLATES.get(template_key, TEMPLATES["clap_basic"])

    # --- Scale template to grid denominator (templates assume 16 steps/bar) ---
    scale_factor = steps_per_bar / 16.0
    scaled_steps = []
    for (step, vel_frac) in template_steps:
        scaled = step * scale_factor
        # Round to nearest integer step
        scaled_int = int(round(scaled))
        if scaled_int < steps_per_bar:
            scaled_steps.append((scaled_int, vel_frac))
    # Deduplicate (two steps may round to same slot)
    seen = {}
    for (step, vel_frac) in scaled_steps:
        if step not in seen:
            seen[step] = vel_frac
    scaled_steps = sorted(seen.items())

    # --- Build note list: (tick_absolute, velocity) ---
    notes: List[Tuple[int, int]] = []
    total_steps = steps_per_bar * bars

    for bar in range(bars):
        # Velocity envelope for fade-in / fade-out transitions
        bar_fraction = bar / max(bars - 1, 1)
        if transition.lower() == "fade in":
            envelope = 0.15 + 0.85 * bar_fraction
        elif transition.lower() == "fade out":
            envelope = 1.0 - 0.80 * bar_fraction
        else:
            envelope = 1.0

        for (step, vel_frac) in scaled_steps:
            abs_step = bar * steps_per_bar + step
            if abs_step >= total_steps:
                continue
            abs_tick = abs_step * ticks_per_step
            # Scale velocity relative to velocity_base (not always 127)
            velocity = max(1, min(127, int(velocity_base * vel_frac * envelope)))
            notes.append((abs_tick, velocity))

    # Sort by tick (should already be, but just in case)
    notes.sort(key=lambda x: x[0])

    # --- Polyphony enforcement (guarantee ≤ polyphony_limit per tick) ---
    # Since each step in our template is unique, polyphony is always 1.
    # But just in case of overlap after scaling, group by tick and keep top N.
    from collections import defaultdict
    tick_groups: dict = defaultdict(list)
    for (tick, vel) in notes:
        tick_groups[tick].append(vel)
    enforced_notes: List[Tuple[int, int]] = []
    for tick in sorted(tick_groups):
        vels = sorted(tick_groups[tick], reverse=True)[:polyphony_limit]
        for vel in vels:
            enforced_notes.append((tick, vel))

    # --- Build MIDI file ---
    mid = mido.MidiFile(type=0, ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    # Tempo
    tempo = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("track_name", name="Drums", time=0))

    # Program change (channel 9 = GM drums, 0-indexed)
    track.append(mido.Message("program_change", channel=9, program=0, time=0))

    # Note duration: one step long (staccato percussion)
    note_duration_ticks = max(1, ticks_per_step // 2)

    # Build delta-time events
    events: List[Tuple[int, str, int]] = []  # (abs_tick, type, velocity)
    for (abs_tick, vel) in enforced_notes:
        events.append((abs_tick, "on", vel))
        events.append((abs_tick + note_duration_ticks, "off", 0))

    events.sort(key=lambda x: (x[0], 0 if x[1] == "off" else 1))

    last_tick = 0
    for (abs_tick, etype, vel) in events:
        delta = abs_tick - last_tick
        if delta < 0:
            delta = 0
        if etype == "on":
            track.append(mido.Message(
                "note_on", channel=9, note=gm_pitch,
                velocity=vel, time=delta
            ))
        else:
            track.append(mido.Message(
                "note_off", channel=9, note=gm_pitch,
                velocity=0, time=delta
            ))
        last_tick = abs_tick

    track.append(mido.MetaMessage("end_of_track", time=0))

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mid.save(str(output_path))

    return mid
