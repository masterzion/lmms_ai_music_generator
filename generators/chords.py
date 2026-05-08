import pretty_midi
import random

def generate_chords(plan, bpm, genre_config, genre):
    """
    Generates 2 to 3 distinct piano tracks with high-end style secrets.
    """
    pianos = []
    num_pianos = random.randint(2, 3)
    
    beat_len = 60.0 / bpm
    bar_len = beat_len * 4.0
    
    for p_idx in range(num_pianos):
        track = pretty_midi.Instrument(program=0) # Piano
        current_time = 0.0
        
        # Style-based role and Frequency-Separated Octave selection
        roles = []
        if genre == "ebm":
            roles = ["mechanical_stabs", "tension_bass", "industrial_percussion", "virtuoso_dense"]
            octave_shifts = [0, -1, 1, 0] # Root, Sub, High, Root
        elif genre == "futurepop":
            roles = ["emotional_arp", "power_chords", "bright_lead", "virtuoso_dense"]
            octave_shifts = [1, 0, 1, 2] # High, Root, High, Very High
        else: # chillout
            roles = ["sparse_motif", "ambient_pad_piano", "soft_arpeggio", "virtuoso_dense"]
            octave_shifts = [0, -1, 0, 1]
            
        role = roles[p_idx % len(roles)]
        octave_shift = octave_shifts[p_idx % len(octave_shifts)] * 12
        
        # Force one of the pianos to be virtuoso_dense if we have 3 pianos
        if p_idx == 2: role = "virtuoso_dense"

        for section in plan["sections"]:
            bars = section["bars"]
            
            # Drops based on role and section
            if "outro" in section["name"].lower() and p_idx > 0: continue
            
            is_solo = "solo" in section["name"].lower()
            
            for b in range(bars):
                if is_solo:
                    # High-end Solo logic
                    if genre == "ebm":
                        for i in range(16):
                            if random.random() > 0.4:
                                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                                pitch = 60 + octave_shift + random.choice([0, 1, 6, 7, 12, 13])
                                track.notes.append(pretty_midi.Note(95, pitch, time, time + 0.08))
                    elif genre == "futurepop":
                        pitches = [60, 64, 67, 71, 72, 74, 76, 79, 83]
                        for i in range(16):
                            time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                            pitch = pitches[i % len(pitches)] + octave_shift
                            track.notes.append(pretty_midi.Note(85, pitch, time, time + 0.15))
                    elif genre == "chillout":
                        if b % 2 == 0:
                            motif = [60, 62, 64, 67, 71, 74, 77]
                            for i in range(4):
                                time = current_time + (b * bar_len) + (i * beat_len)
                                pitch = random.choice(motif) + octave_shift
                                track.notes.append(pretty_midi.Note(60, pitch, time, time + beat_len * 1.5))
                else:
                    # Accompaniment with frequency separation
                    if genre == "ebm":
                        if role == "mechanical_stabs":
                            for i in [0, 3, 6, 9, 12]:
                                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                                track.notes.append(pretty_midi.Note(80, 40 + octave_shift, time, time + 0.1))
                        elif role == "tension_bass":
                            for i in [0, 8]:
                                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                                track.notes.append(pretty_midi.Note(90, 36 + octave_shift, time, time + 0.2))

                    elif genre == "futurepop":
                        if role == "emotional_arp":
                            pitches = [60, 64, 67, 72, 74, 76, 79]
                            for i, p in enumerate(pitches):
                                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                                track.notes.append(pretty_midi.Note(70, p + octave_shift, time, time + beat_len))
                        elif role == "power_chords":
                            for i in [0, 4, 8, 12]:
                                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                                for p in [48, 55, 60]:
                                    track.notes.append(pretty_midi.Note(85, p + octave_shift, time, time + 0.4))

                    elif genre == "chillout":
                        if role == "sparse_motif":
                            if b % 2 == 0:
                                pitches = [48, 64, 67, 74] # Open Drop-2 Cmaj9
                                for i, p in enumerate(pitches):
                                    time = current_time + (b * bar_len) + (i * beat_len * 0.5)
                                    track.notes.append(pretty_midi.Note(50, p + octave_shift, time, time + 2.5))
                        elif role == "soft_arpeggio":
                            for i in range(8):
                                if random.random() > 0.6:
                                    time = current_time + (b * bar_len) + (i * beat_len / 2.0)
                                    track.notes.append(pretty_midi.Note(45, 72 + random.choice([0, 2, 4, 7]) + octave_shift, time, time + 1.0))
                                    
                    if role == "virtuoso_dense":
                        for i in range(16):
                            if random.random() > 0.3:
                                time = current_time + (b * bar_len) + (i * beat_len / 4.0)
                                pitch = 60 + octave_shift + random.choice([0, 3, 7, 10, 12, 15]) 
                                track.notes.append(pretty_midi.Note(65, pitch, time, time + 0.1))

            current_time += bars * bar_len
        pianos.append(track)
        
    return pianos
