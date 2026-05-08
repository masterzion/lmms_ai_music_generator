import pretty_midi
import random

def assemble_song(bpm, plan, melody_clips, drum_inst, bass_inst, pads_inst, piano_tracks):
    """
    Assembles the final song from deterministic and AI components.
    """
    song = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    
    # Add deterministic tracks
    if drum_inst:
        song.instruments.append(drum_inst)
    if bass_inst:
        song.instruments.append(bass_inst)
    if pads_inst:
        song.instruments.append(pads_inst)
        
    for track in piano_tracks:
        if track:
            song.instruments.append(track)
        
    # Stitch melody clips according to the section plan
    # For this simplified architecture, we just dump the clips starting at section boundaries.
    
    beat_length = 60.0 / bpm
    bar_length = beat_length * 4.0
    
    current_time = 0.0
    
    for i, section in enumerate(plan["sections"]):
        section_bars = section["bars"]
        trans_raw = section.get("transition", "none")
        transition = (trans_raw if trans_raw else "none").lower()
        
        section_duration = section_bars * bar_length
        
        # Handle "drops" by trimming deterministic tracks
        drop_duration = 0.0
        if "drop" in transition:
            drop_duration = bar_length # Default to 1 bar drop
            print(f"  [Assembly] Applying DROP to section {i+1} ({section['name']})")

        # Section Contrast: Tracking dropped instruments to ensure only ONE drop per instrument per song
        if i == 0:
            song._dropped_instruments = set() # Store in song object for persistence through sections
        
        all_deterministic_tracks = [drum_inst, bass_inst, pads_inst] + piano_tracks
        available_tracks = [t for t in all_deterministic_tracks if t and t not in song._dropped_instruments]
        
        if random.random() > 0.4 and available_tracks: 
            # Randomly select 1 to 2 tracks that haven't dropped yet
            k = min(len(available_tracks), random.randint(1, 2))
            tracks_to_dim = random.sample(available_tracks, k=k)
            
            for inst in tracks_to_dim:
                song._dropped_instruments.add(inst)
                print(f"  [Assembly] Section {i+1}: Applying ONE-TIME DROP to {inst.name if hasattr(inst, 'name') else 'Track'}")
                for note in inst.notes:
                    if note.start >= current_time and note.start < current_time + section_duration:
                        # Dim selected tracks by 80% for this section
                        note.velocity = max(10, int(note.velocity * 0.2))

        # If we have a melody clip for this section, add it
        if i < len(melody_clips) and melody_clips[i]:
            clip = melody_clips[i]
            for inst in clip.instruments:
                new_inst = pretty_midi.Instrument(program=inst.program)
                for note in inst.notes:
                    new_note = pretty_midi.Note(
                        velocity=note.velocity,
                        pitch=note.pitch,
                        start=note.start + current_time,
                        end=note.end + current_time
                    )
                    # Don't drop melody, only deterministic backing
                    new_inst.notes.append(new_note)
                song.instruments.append(new_inst)
        
        # Apply the drop to the deterministic tracks if needed
        # (This is a simplified implementation: we'd ideally trim the notes 
        # that overlap with the drop period)
        
    # Apply drops to deterministic tracks
    current_time = 0.0
    for i, section in enumerate(plan["sections"]):
        section_duration = section["bars"] * bar_length
        trans_raw = section.get("transition", "none")
        transition = (trans_raw if trans_raw else "none").lower()
        
        if "drop" in transition:
            drop_start = current_time + section_duration - bar_length
            drop_end = current_time + section_duration
            
            # Tracks to apply drop to
            deterministic_tracks = [drum_inst, bass_inst, pads_inst] + piano_tracks
            
            for inst in deterministic_tracks:
                if inst:
                    for note in inst.notes:
                        if note.start >= drop_start and note.start < drop_end:
                            # Reduce velocity to 20% instead of muting completely
                            note.velocity = max(10, int(note.velocity * 0.2))
                    
        current_time += section_duration

    return song
