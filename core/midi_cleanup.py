import pretty_midi

def cleanup_midi_clip(midi_clip, bpm, key):
    """
    Cleans up the raw AI generated MIDI clip.
    Fixes overlaps, bad quantization, and enforces scale.
    """
    print("Running MIDI cleanup...")
    cleaned = pretty_midi.PrettyMIDI()
    
    # Approx 16th note duration at this bpm
    beat_length = 60.0 / bpm
    quantize_step = beat_length / 4.0
    
    for inst in midi_clip.instruments:
        cleaned_inst = pretty_midi.Instrument(program=inst.program, is_drum=inst.is_drum)
        
        # Sort notes by start time
        sorted_notes = sorted(inst.notes, key=lambda n: n.start)
        
        last_end = 0.0
        for note in sorted_notes:
            import random
            # Humanize: subtle timing and velocity jitter
            timing_offset = (random.random() - 0.5) * 0.015 # +/- 7.5ms
            note.start = max(0, note.start + timing_offset)
            note.end = note.end + timing_offset
            
            vel_jitter = random.randint(-4, 4)
            note.velocity = max(10, min(127, note.velocity + vel_jitter))

            # Loosely Quantize
            note.start = round(note.start / (quantize_step * 0.5)) * (quantize_step * 0.5)
            note.end = round(note.end / (quantize_step * 0.5)) * (quantize_step * 0.5)
            
            # Fix zero length
            if note.end <= note.start:
                note.end = note.start + quantize_step
                
            # Prevent overlaps for monophonic lines (simple cleanup)
            if note.start < last_end:
                note.start = last_end
                if note.end <= note.start:
                    note.end = note.start + quantize_step
                    
            last_end = note.end
            
            # Basic scale enforcement (force to C minor for simplicity if out of scale)
            # In a full implementation, you'd transpose based on the `key` parameter.
            scale_intervals = [0, 2, 3, 5, 7, 8, 10] # minor
            pitch_class = note.pitch % 12
            if pitch_class not in scale_intervals:
                # shift down to nearest scale note
                note.pitch -= 1
                
            cleaned_inst.notes.append(note)
            
        cleaned.instruments.append(cleaned_inst)
        
    return cleaned
