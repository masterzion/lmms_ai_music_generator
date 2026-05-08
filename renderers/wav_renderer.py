import subprocess
import os

def render_custom_wav(midi_input, wav_output):
    """
    Renders a specific MIDI file to a specific WAV file.
    """
    soundfont = "soundfonts/FluidR3_GM.sf2"
    
    if not os.path.exists(midi_input):
        print(f"Error: {midi_input} not found.")
        return

    print(f"  Rendering {midi_input} to {wav_output}...", flush=True)
    
    cmd = [
        "fluidsynth",
        "-ni",
        "-F", wav_output,
        "-r", "44100",
        soundfont,
        midi_input
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  SUCCESS: WAV rendered.", flush=True)
    except Exception as e:
        print(f"  FAILED: WAV rendering failed: {e}", flush=True)
