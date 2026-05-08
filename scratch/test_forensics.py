import os
import sys

# Ensure local imports work
sys.path.append(os.getcwd())

from llm.prompt_expander import expand_prompt
from llm.planner import create_song_plan

def test_forensic_pipeline():
    genres = ["futurepop", "ebm", "chillout"]
    topic = "Digital Echoes"
    
    for genre in genres:
        print(f"\n{'='*60}")
        print(f"TESTING GENRE: {genre}")
        print(f"{'='*60}")
        
        print("\n--- STEP 1: PROMPT EXPANSION ---")
        expanded = expand_prompt(genre, topic)
        print(f"EXPANDED PROMPT PREVIEW:\n{expanded[:300]}...")
        
        # Check if forensic terms exist in expansion
        if genre == "futurepop" and ("grid" in expanded.lower() or "polyphony" in expanded.lower()):
            print("SUCCESS: Forensic terms found in Futurepop expansion!")
        elif genre == "ebm" and ("staccato" in expanded.lower() or "bassline" in expanded.lower()):
             print("SUCCESS: Forensic terms found in EBM expansion!")
             
        print("\n--- STEP 2: SONG PLANNING ---")
        plan = create_song_plan(expanded, genre=genre)
        
        # Verify JSON structure
        first_section = plan.get("sections", [{}])[0]
        first_track = first_section.get("tracks", [{}])[0]
        
        print(f"SAMPLE TRACK FROM PLAN:")
        print(f"  Name: {first_track.get('name')}")
        print(f"  Grid: {first_track.get('grid')}")
        print(f"  Polyphony: {first_track.get('polyphony')}")
        print(f"  Pitch Range: {first_track.get('pitch_range')}")
        
        if first_track.get("grid"):
            print("SUCCESS: Forensic JSON fields populated in plan!")

if __name__ == "__main__":
    test_forensic_pipeline()
