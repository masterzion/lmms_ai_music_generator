import subprocess
import os

def render_custom_wav(midi_input, wav_output, genre="chillout"):
    """
    Renders a specific MIDI file to a specific WAV file and applies forensic EQ.
    """
    soundfont = "soundfonts/FluidR3_GM.sf2"
    temp_wav = wav_output + ".tmp.wav"
    
    if not os.path.exists(midi_input):
        print(f"Error: {midi_input} not found.")
        return

    print(f"  Rendering {midi_input} to {wav_output}...", flush=True)
    
    # 1. Render to temporary WAV
    cmd_render = [
        "fluidsynth", "-ni", "-F", temp_wav, "-r", "44100", soundfont, midi_input
    ]
    
    try:
        subprocess.run(cmd_render, check=True, capture_output=True)
        
        # 2. Apply Forensic EQ via FFmpeg
        # Sub-bass boost for all, Shimmer for specific genres
        filters = "bass=g=6:f=50:w=0.5" # Universal sub-bass grounding
        if genre in ["chillout", "futurepop"]:
            filters += ",treble=g=8:f=12000:w=0.5" # Forensic Shimmer
            
        cmd_eq = [
            "ffmpeg", "-y", "-i", temp_wav, "-af", filters, wav_output
        ]
        
        subprocess.run(cmd_eq, check=True, capture_output=True)
        
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
            
        print(f"  SUCCESS: Forensic WAV rendered with EQ.", flush=True)
    except Exception as e:
        print(f"  FAILED: WAV rendering/EQ failed: {e}", flush=True)
