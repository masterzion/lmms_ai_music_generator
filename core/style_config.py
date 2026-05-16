# MIDI note reference:
# C1=24  C2=36  C3=48  C4=60  C5=72  C6=84  C7=96
# Each instrument_ranges entry: [min_midi, max_midi]

STYLE_DATA = {
    "ebm": {
        "bpm_ranges": [[130, 140], [140, 155]],
        "common_instruments": [
            "MS-20 Bass", "Chainsaw Lead", "Industrial Noise Hit",
            "Crushed Sub", "Sequenced Pulse", "Gated Snare",
            "Metallic Percussion", "Vocoder Grunt", "FM Stab"
        ],
        # Pitch ranges per instrument (MIDI note numbers)
        # Low and narrow = menacing. Leads stay in upper-mid for piercing quality.
        "instrument_ranges": {
            "MS-20 Bass":           [24, 48],   # C1–C3: deep, punishing sub range
            "Chainsaw Lead":        [55, 79],   # G3–G5: mid-upper for aggression
            "Industrial Noise Hit": [36, 60],   # C2–C4: percussive noise hits
            "Crushed Sub":          [24, 43],   # C1–G2: extreme low end
            "Sequenced Pulse":      [36, 60],   # C2–C4: mechanical mid-range pulse
            "Gated Snare":          [38, 38],   # GM Snare (fixed)
            "Metallic Percussion":  [39, 51],   # GM Clap to Ride
            "Vocoder Grunt":        [48, 67],   # C3–G4: voice-range harmonics
            "FM Stab":              [55, 72],   # G3–C5: sharp attack stabs
        },
        # Locrian and Phrygian = most dissonant, aggressive, and dark scales
        "harmonies": ["Locrian (Maximum Tension)", "Phrygian Dominant", "Chromatic Cluster", "Dissonant Minor 2nd"],
        "effects": ["Bitcrusher", "Heavy Distortion", "Bandpass Filter", "Gated Reverb", "Ring Modulator"],
        "piano_solo_style": "Harsh, dissonant, monophonic stabs. Short, aggressive, relentless. No melodic resolution. Phrygian or Locrian mode only.",
        "pipeline": {
            "min_tracks": 10, "max_tracks": 14,
            "min_bars": 125, "max_bars": 175,
            "minor_only": True,
            "melody_density": 0.75,
            "drum_density": 1.0,
            "humanization": 0.0,
            "bass_repetition": 0.98,
            "max_polyphony": 2,     # Monophonic = heavier, more industrial
            "velocity_base": 120,   # Near-maximum, punishing
            "section_density": {
                "Intro":     [0.6, 0.8],
                "Verse":     [0.85, 1.0],
                "Build-up":  [0.9,  1.0],
                "Main Drop": [1.0,  1.0],
                "Breakdown": [0.5,  0.7],
                "Outro":     [0.4,  0.6],
            }
        }
    },

    "futurepop": {
        # Real Futurepop BPM: VNV Nation, Assemblage 23, Covenant = 130-150 BPM
        "bpm_ranges": [[130, 140], [140, 150]],
        "common_instruments": [
            "Trance Lead", "Super Saw", "Driving Sequencer",
            "Sidechained Pad", "Gated Strings", "Fast Arpeggio",
            "Club Kick", "Vocoder FX", "Pulsing Bass"
        ],
        # Pitch ranges per instrument
        # Pulsing bass stays low. Leads soar in the upper register for emotional impact.
        "instrument_ranges": {
            "Trance Lead":       [60, 84],   # C4–C6: soaring lead melody
            "Super Saw":         [52, 76],   # E3–E5: rich mid-range chord stabs
            "Driving Sequencer": [36, 60],   # C2–C4: mechanical bass sequencer
            "Sidechained Pad":   [48, 72],   # C3–C5: pumping atmospheric pad
            "Gated Strings":     [48, 79],   # C3–G5: dramatic string swells
            "Fast Arpeggio":     [55, 84],   # G3–C6: fast upper-register arpeggios
            "Club Kick":         [36, 36],   # GM Bass Drum (fixed)
            "Vocoder FX":        [48, 67],   # C3–G4: vocal harmonics
            "Pulsing Bass":      [28, 48],   # E1–C3: deep driving bass
        },
        # Aeolian/Harmonic Minor = melancholic but not happy. No major modes.
        "harmonies": ["Aeolian (Melancholic)", "Harmonic Minor", "Dorian (Dark Groove)", "Suspended 4th"],
        "effects": ["Ping-Pong Delay", "Large Hall Reverb", "Sidechain (Pumping)", "Phaser", "Stereo Widener"],
        "piano_solo_style": "Melancholic but propulsive. Minor key arpeggios with emotional but restrained phrasing. Dance-oriented pulse, never triumphant.",
        "pipeline": {
            "min_tracks": 10, "max_tracks": 16,
            "min_bars": 160, "max_bars": 220,
            "minor_only": True,     # Always minor = never 'happy'
            "melody_density": 0.65,
            "drum_density": 0.95,
            "humanization": 0.02,
            "bass_repetition": 0.80,
            "max_polyphony": 6,
            "velocity_base": 95,
            "section_density": {
                "Intro":     [0.3,  0.5],
                "Verse":     [0.6,  0.75],
                "Build-up":  [0.75, 0.9],
                "Main Drop": [0.9,  1.0],
                "Breakdown": [0.35, 0.55],
                "Outro":     [0.25, 0.45],
            }
        }
    },

    "chillout": {
        "bpm_ranges": [[70, 80], [80, 88]],   # Slower = more relaxing
        "common_instruments": [
            "Fender Rhodes", "Warm Sine Bass", "Lush Pad",
            "Tibetan Bowls", "Lofi Kick", "Soft Rimshot",
            "Ambient Drone", "Ethereal Flute", "Vibraphone"
        ],
        # Pitch ranges per instrument
        # Wide open ranges, centered in comfortable mid-register. Nothing harsh.
        "instrument_ranges": {
            "Fender Rhodes":  [48, 72],   # C3–C5: classic Rhodes sweet spot
            "Warm Sine Bass": [28, 52],   # E1–E3: warm low-mid bass
            "Lush Pad":       [48, 79],   # C3–G5: wide atmospheric pad
            "Tibetan Bowls":  [55, 79],   # G3–G5: resonant bowl tones
            "Lofi Kick":      [36, 36],   # GM Bass Drum (fixed)
            "Soft Rimshot":   [37, 37],   # GM Side Stick (fixed)
            "Ambient Drone":  [36, 60],   # C2–C4: deep, slow drone
            "Ethereal Flute": [65, 89],   # F4–F6: high, breathy flute tones
            "Vibraphone":     [53, 77],   # F3–F5: mellow vibraphone range
        },
        # Neutral harmonies — no strong tension, no strong resolution
        "harmonies": ["Sus2 (Neutral Float)", "Major 9th (Open)", "Whole Tone (Dreamy)", "Pentatonic (Safe)", "Modal (Ambiguous)"],
        "effects": ["Long Tail Reverb", "Soft Low-Pass Filter", "Gentle Chorus", "Slow Tremolo", "Vinyl Warmth"],
        "piano_solo_style": "Minimal, spacious. Long silences between notes. No strong leading tones. Neutral, floating, impressionistic. Satie-like.",
        "pipeline": {
            "min_tracks": 8, "max_tracks": 12,
            "min_bars": 100, "max_bars": 138,
            "minor_only": False,    # Neutral — can be major or minor
            "melody_density": 0.15, # Very sparse — silence is the instrument
            "drum_density": 0.25,   # Very soft percussion
            "humanization": 0.20,   # Human, breathing feel
            "bass_repetition": 0.45,
            "max_polyphony": 4,
            "velocity_base": 55,    # Whisper-quiet
            "section_density": {
                "Intro":     [0.05, 0.15],
                "Verse":     [0.15, 0.30],
                "Build-up":  [0.25, 0.40],
                "Main Drop": [0.35, 0.50],
                "Breakdown": [0.10, 0.20],
                "Outro":     [0.05, 0.15],
            }
        }
    }
}
