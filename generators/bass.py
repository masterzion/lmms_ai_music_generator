import pretty_midi
import random

def generate_bass(plan, bpm, genre_config):
    """
    Generates a style-specific bassline following researched production techniques.
    """
    track = pretty_midi.Instrument(program=38) # Synth Bass
    beat_len = 60.0 / bpm
    bar_len = beat_len * 4.0
    current_time = 0.0
    
    # Identify genre from config
    # We'll detect it based on BPM if not explicitly passed
    genre = "chillout"
    if 110 <= bpm <= 130: genre = "ebm"
    elif bpm > 130: genre = "futurepop"

    for section in plan["sections"]:
        bars = section["bars"]
        for b in range(bars):
            if genre == "ebm":
                # EBM Secret: Driving 16th notes with octave jumps and velocity bite
                for i in range(16):
                    time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                    pitch = 36 if i % 4 != 3 else 48 # Octave jump on every 4th 16th
                    vel = 100 if i % 4 == 0 else 75 # Accent the main beats
                    track.notes.append(pretty_midi.Note(vel, pitch, time, time + 0.1))
            
            elif genre == "futurepop":
                # Futurepop Secret: Sidechained 'pumping' feel (gap on the beat)
                for i in range(16):
                    if i % 4 != 0: # Silence on 1, 2, 3, 4 for the kick
                        time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                        track.notes.append(pretty_midi.Note(90, 36, time, time + 0.15))
            
            else:
                # Chillout Secret: Rounded sub-bass, long notes, sparse
                for beat in [0, 2]:
                    time = current_time + (b * bar_len) + (beat * beat_len)
                    track.notes.append(pretty_midi.Note(65, 36, time, time + beat_len * 1.8))
                    
        current_time += bars * bar_len
        
    return track
