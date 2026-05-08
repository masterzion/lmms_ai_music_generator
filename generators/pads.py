import pretty_midi

def generate_pads(plan, bpm, genre_config):
    """
    Generates a deterministic pad track based on the song plan.
    Provides sustained atmospheric backing.
    """
    track = pretty_midi.Instrument(program=91) # Pad 4 (choir)
    
    beat_len = 60.0 / bpm
    bar_len = beat_len * 4.0
    current_time = 0.0
    
    for section in plan["sections"]:
        duration = section["bars"] * bar_len
        
        # Simple root-note pad for the section
        # We'll use E2 (40) for now as a default if key parsing fails
        pitch = 40 
        
        note = pretty_midi.Note(
            velocity=60,
            pitch=pitch,
            start=current_time,
            end=current_time + duration
        )
        track.notes.append(note)
        current_time += duration
        
    return track
