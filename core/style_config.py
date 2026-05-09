STYLE_DATA = {
    "ebm": {
        "bpm_ranges": [[110, 120], [120, 130]],
        "common_instruments": ["MS-20 Bass", "Distorted Lead", "Metallic Percussion", "Factory Noise", "Sequenced Sub", "Authoritative Shouts", "Gated Snare", "FM Synth"],
        "harmonies": ["Phrygian Dominant", "Natural Minor", "Locrian (Tension)", "Pentatonic Minor"],
        "structures": [
            "Intro -> Loop Build -> Verse -> Chorus -> Bridge -> Climax -> Outro",
            "Factory Intro -> Mechanical Groove -> Vocal Command -> Breakdown -> Full Assault -> Outro"
        ],
        "effects": ["Bitcrusher", "Bandpass Filter", "Heavy Distortion", "Gated Reverb", "Sidechain Compression"],
        "piano_solo_style": "Dissonant, aggressive, highly rhythmic stabs, minor 2nd intervals, high-pitched piercing runs.",
        "pipeline": {
            "min_tracks": 10, "max_tracks": 14,
            "min_bars": 128, "max_bars": 180,
            "minor_only": True, "melody_density": 0.2,
            "drum_density": 1.0, "humanization": 0.0, "bass_repetition": 0.95
        }
    },
    "futurepop": {
        "bpm_ranges": [[180, 240], [240, 280]],
        "common_instruments": ["Church Organ", "Drawbar Organ", "Trance Lead", "Super Saw", "Sidechained Pad", "Gated Strings", "Fast Arpeggio", "Club Kick", "Emotional Piano", "Vocoder FX", "Choir Aahs"],
        "harmonies": ["Aeolian (Melancholic)", "Dorian (Uplifting Minor)", "Harmonic Minor", "Suspended 4th Chords"],
        "structures": [
            "Atmospheric Intro -> Verse -> Build-up -> Anthem Chorus -> Breakdown -> Final Chorus -> Outro",
            "Club Intro -> Groove Verse -> Emotional Lift -> Main Hook -> Instrumental Break -> Outro"
        ],
        "effects": ["Ping-Pong Delay", "Large Hall Reverb", "Phaser", "Sidechain (Pumping)", "High-Shelf Boost"],
        "piano_solo_style": "Uplifting, fast arpeggios, melodic octaves, anthem-like emotional progression.",
        "pipeline": {
            "min_tracks": 12, "max_tracks": 24,
            "min_bars": 220, "max_bars": 360,
            "minor_only": False, "melody_density": 0.8,
            "drum_density": 0.9, "humanization": 0.05, "bass_repetition": 0.7
        }
    },
    "chillout": {
        "bpm_ranges": [[80, 90], [90, 110]],
        "common_instruments": ["Fender Rhodes", "Warm Sine Bass", "Lush Pad", "Nature Samples (Ocean/Rain)", "Lofi Kick", "Rimshot", "Vocal Chops", "Ethereal Flute"],
        "harmonies": ["Major 7th Chords", "Minor 9th Chords", "Add 9", "Sus 2", "Jazz Progressions"],
        "structures": [
            "Ambient Intro -> Circular Groove -> Floating Melody -> Deep Expansion -> Hypnotic Fade",
            "Pad Intro -> Bass Groove -> Chill Melody -> Minimal Breakdown -> Atmospheric Outro"
        ],
        "effects": ["Vinyl Crackle", "Long Tail Reverb", "Soft Low-Pass Filter", "Chorus", "Ping-Pong Delay"],
        "piano_solo_style": "Expressive, sparse, jazz-inflected runs, bluesy motifs, long sustain, Satie-esque minimalism.",
        "pipeline": {
            "min_tracks": 10, "max_tracks": 16,
            "min_bars": 100, "max_bars": 160,
            "minor_only": False, "melody_density": 0.3,
            "drum_density": 0.4, "humanization": 0.15, "bass_repetition": 0.5
        }
    }
}
