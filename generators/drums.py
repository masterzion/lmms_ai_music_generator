import pretty_midi
import random

def generate_drums(plan, bpm, genre_config):
    """
    Generates a deterministic drum track with genre-aware density and humanization.
    """
    track = pretty_midi.Instrument(program=0, is_drum=True)
    
    beat_len = 60.0 / bpm
    bar_len = beat_len * 4.0
    current_time = 0.0
    
    density = genre_config.get("drum_density", 1.0)
    humanize = genre_config.get("humanization", 0.05)
    
    for section in plan["sections"]:
        bars = section["bars"]
        
        for b in range(bars):
            for i in range(16): # 16th notes
                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                
                # Kick on 1 and 3 (with density scaling)
                if i in [0, 8] and random.random() < density:
                    track.notes.append(pretty_midi.Note(80, 36, time, time + 0.1))
                
                # Snare on 4 and 12
                if i in [4, 12]:
                    vel = 90 + (random.random() - 0.5) * 20 * humanize
                    track.notes.append(pretty_midi.Note(int(vel), 38, time, time + 0.1))
                
                # Hi-hats
                if i % 2 == 0 and random.random() < density:
                    vel = 60 + (random.random() - 0.5) * 40 * humanize
                    track.notes.append(pretty_midi.Note(int(vel), 42, time, time + 0.1))
                    
        current_time += bars * bar_len
        
    return track
