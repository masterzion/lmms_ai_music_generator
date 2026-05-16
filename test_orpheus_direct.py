import requests
import json

API_URL = "http://127.0.0.1:9000"

dummy_plan = {
    "title": "Orpheus Test Song",
    "bpm": 145,
    "key": "D# minor",
    "genre": "ebm",
    "sections": [
        {
            "name": "Intro",
            "bars": 16,
            "tracks": [
                {
                    "id": "track1",
                    "name": "MS-20 Bass",
                    "midi_prompt": "Aggressive industrial pulse",
                    "seed_note": 27, # D#1
                    "polyphony": 1,
                    "density": 1.0,
                    "pitch_range": [24, 48],
                    "is_drum": False,
                    "program": 38 # Synth Bass 1
                }
            ]
        }
    ]
}

def test_direct():
    print("--- Sending Dummy Plan to Orpheus ---")
    res = requests.post(f"{API_URL}/generate_from_plan", json={"plan": dummy_plan})
    print(f"RESPONSE: {res.json()}")

if __name__ == "__main__":
    test_direct()
