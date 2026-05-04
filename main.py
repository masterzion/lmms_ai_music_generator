import argparse
import os
import json
from src.composer import Composer
from src.engine import SequencerEngine
from src.schema import Composition

def main():
    parser = argparse.ArgumentParser(description="Music Maker: LLM Composer & Python Sequencer")
    parser.add_argument("--prompt", type=str, help="Musical prompt for the LLM", default="A dark EBM track at 128 BPM in A minor")
    parser.add_argument("--output", type=str, help="Output MIDI filename", default="output/composition.mid")
    parser.add_argument("--mock", action="store_true", help="Use a mock composition instead of calling the LLM")
    parser.add_argument("--model", type=str, default="llama3:8b", help="Ollama model name")
    
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    if args.mock:
        print("Using mock composition...")
        # A simple EBM-style mock for testing
        mock_data = {
            "meta": {"bpm": 128, "scale": "A_minor", "swing": 0.0},
            "structure": [{"section": "A", "bars": 4}],
            "tracks": {
                "drums": {
                    "type": "drum_machine",
                    "patterns": {
                        "A": {
                            "kick": "X---X---X---X---",
                            "snare": "----X-------X---",
                            "hat": "X-X-X-X-X-X-X-X-"
                        }
                    }
                },
                "bass": {
                    "type": "monophonic",
                    "root": "A1",
                    "patterns": {"A": [0,0,3,0, 0,0,5,0, 0,0,3,0, 0,0,7,0]}
                }
            }
        }
        composition = Composition(**mock_data)
    else:
        print(f"Connecting to LLM ({args.model})...")
        composer = Composer(model_name=args.model)
        try:
            composition = composer.compose(args.prompt)
        except Exception as e:
            print(f"Failed to get composition from LLM: {e}")
            return

    print(f"Generating MIDI for composition: {composition.meta.scale} @ {composition.meta.bpm} BPM")
    engine = SequencerEngine(composition)
    midi_data = engine.generate()
    
    midi_data.write(args.output)
    print(f"Success! MIDI saved to {args.output}")

if __name__ == "__main__":
    main()
