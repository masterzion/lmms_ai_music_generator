# API Configuration
MIDI_LLM_API_BASE = "http://192.168.2.188:9000"
OLLAMA_API_BASE = "http://192.168.2.188:11434"

GENRES = {
    "ebm": {
        "bpm": [110, 130],
        "min_tracks": 10,
        "max_tracks": 14,
        "min_bars": 128,
        "max_bars": 180,
        "minor_only": True,
        "melody_density": 0.2,
        "drum_density": 1.0,
        "humanization": 0.0,
        "bass_repetition": 0.95
    },
    "futurepop": {
        "bpm": [130, 145],
        "min_tracks": 12,
        "max_tracks": 24,
        "min_bars": 144,
        "max_bars": 210,
        "minor_only": False,
        "melody_density": 0.8,
        "drum_density": 0.9,
        "humanization": 0.05,
        "bass_repetition": 0.7
    },
    "chillout": {
        "bpm": [80, 110],
        "min_tracks": 10,
        "max_tracks": 16,
        "min_bars": 80,
        "max_bars": 130,
        "minor_only": False,
        "melody_density": 0.3,
        "drum_density": 0.4,
        "humanization": 0.15,
        "bass_repetition": 0.5
    }
}
