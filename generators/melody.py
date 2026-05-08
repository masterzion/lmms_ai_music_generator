from llm.midi_llm_client import generate_midi_clip

def generate_melody(plan):
    """
    Orchestrates the AI generation of melody clips using MIDI-LLM.
    Returns a list of pretty_midi objects corresponding to each section.
    """
    clips = []
    
    prompts = { p["section"]: p["prompt"] for p in plan.get("midi_prompts", []) }
    
    for i, section in enumerate(plan["sections"]):
        section_name = section["name"]
        
        # Check if we have a prompt for this section
        if section_name in prompts:
            prompt = prompts[section_name]
            print(f"  Section {i+1} ({section_name}): Prompting AI for '{prompt}'...", flush=True)
            
            # Call the real MIDI-LLM architecture
            clip = generate_midi_clip(prompt)
            if clip:
                print(f"  Section {i+1}: AI clip received.", flush=True)
            else:
                print(f"  Section {i+1}: AI failed to return clip (API might be loading or offline).", flush=True)
                
            clips.append(clip)
        else:
            print(f"  Section {i+1} ({section_name}): No specific AI prompt found, skipping.", flush=True)
            clips.append(None)
            
    return clips
