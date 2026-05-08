import pretty_midi
import os
import glob

def analyze_midis(output_dir):
    midi_files = glob.glob(os.path.join(output_dir, "**/*.mid"), recursive=True)
    
    if not midi_files:
        print("No MIDI files found.")
        return

    for midi_file in midi_files:
        print(f"\nAnalyzing: {os.path.basename(midi_file)}")
        print("-" * 50)
        try:
            midi_data = pretty_midi.PrettyMIDI(midi_file)
            for i, track in enumerate(midi_data.instruments):
                name = track.name if track.name else f"Track {i+1}"
                # Try to guess instrument name if no name
                if not track.name:
                    name = pretty_midi.program_to_instrument_name(track.program)
                
                print(f"  {name:25} | Notes: {len(track.notes):5}")
        except Exception as e:
            print(f"  Error reading {midi_file}: {e}")

if __name__ == "__main__":
    analyze_midis("/media/master/ssd/music_maker/batch_client/outputs")
