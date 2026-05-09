from llm.midi_llm_client import generate_midi_clip

def generate_melody(plan):
    """
    Orchestrates the AI generation of melody clips using MIDI-LLM and forensic parameters.
    """
    # We now return a list of lists: [[tracks for section 1], [tracks for section 2], ...]
    section_clips = []
    
    for i, section in enumerate(plan["sections"]):
        section_name = section["name"]
        tracks_in_section = []
        
        print(f"  Section {i+1} ({section_name}): Processing {len(section.get('tracks', []))} tracks...", flush=True)
        
        for track_plan in section.get("tracks", []):
            is_drum = track_plan.get("is_drum", False)
            
            prompt = track_plan["midi_prompt"]
            # Forensic enhancement of the prompt
            enhanced_prompt = (
                f"{prompt}. Style: {track_plan.get('grid', '1/16 notes')}. "
                f"Density: {track_plan.get('density', 0.5)}. "
                f"Max Polyphony: {track_plan.get('polyphony', 1)}. "
                f"Range: MIDI {track_plan.get('pitch_range', [36, 84])}."
            )
            
            print(f"    - Generating '{track_plan['name']}' {'(Drum)' if is_drum else ''}...", flush=True)
            clip = generate_midi_clip(enhanced_prompt)
            if clip:
                # Apply track name and drum status to the instrument in the clip
                for inst in clip.instruments:
                    inst.name = track_plan["name"]
                    inst.is_drum = is_drum
                tracks_in_section.append(clip)
            else:
                tracks_in_section.append(None)
                
        section_clips.append(tracks_in_section)
            
    return section_clips
