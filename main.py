import argparse
import os
import json
from src.composer import Composer
from src.engine import SequencerEngine
from src.schema import Composition

def main():
    parser = argparse.ArgumentParser(description="Pro AI Music Sequencer")
    parser.add_argument("--concept", type=str, required=True, help="Style + Theme (e.g., 'EBM about World War 2')")
    parser.add_argument("--model", type=str, default="llama3:8b", help="Ollama model name")
    parser.add_argument("--monolithic", action="store_true", help="EXPERIMENTAL: Generate entire song in one handshake")
    parser.add_argument("--render", action="store_true", help="Render MIDI to WAV via Steam Deck")
    
    args = parser.parse_args()

    # --- LIBRARIAN PHASE ---
    # Find existing folders to help the AI organize
    base_output = "output"
    existing_folders = []
    if os.path.exists(base_output):
        for root, dirs, files in os.walk(base_output):
            if root != base_output:
                existing_folders.append(os.path.relpath(root, base_output))
    
    folder_context = f"Existing folders for inspiration: {', '.join(existing_folders) if existing_folders else 'None'}"
    full_concept = f"{args.concept}. {folder_context}"

    max_retries = 3
    current_attempt = 1
    active_prompt = full_concept

    print(f"--- Creative Director & Librarian: Starting session for '{args.concept}' ---")
    composer = Composer(model_name=args.model)
    
    while current_attempt <= max_retries:
        try:
            if args.monolithic:
                composition = composer.compose_monolithic(active_prompt)
            else:
                composition = composer.compose(active_prompt, context=folder_context)
        except Exception as e:
            print(f"Failed to generate composition: {e}")
            return

        if not composition:
            return

        print(f"Librarian: Sorting '{composition.meta.title}' into {composition.meta.genre}/{composition.meta.folder}")
        
        engine = SequencerEngine(composition)
        midi_data = engine.generate()
        
        # --- QA AGENT: AUTO-REJECTION LOOP ---
        silent_tracks = []
        for inst in midi_data.instruments:
            if len(inst.notes) == 0:
                silent_tracks.append(inst.name)
                
        if silent_tracks and current_attempt < max_retries:
            print(f"\n[QA AGENT] REJECTED: Silent tracks detected ({', '.join(silent_tracks)}).")
            print(f"[QA AGENT] Auto-correcting and maintaining context for Attempt {current_attempt + 1}...\n")
            
            # Maintain context and force the AI to correct its mistake
            active_prompt = f"{full_concept}\n\nQA SYSTEM FEEDBACK FROM PREVIOUS ATTEMPT (DO NOT REPEAT THIS MISTAKE):\nThe previous composition was REJECTED because the following tracks generated 0 notes: {', '.join(silent_tracks)}. You MUST fix this. 0-note tracks are strictly forbidden."
            current_attempt += 1
            continue
        elif silent_tracks:
            print(f"\n[QA AGENT] WARNING: Max retries ({max_retries}) reached. Proceeding with silent tracks.\n")
            break
        else:
            print(f"\n[LOCAL QA] PASSED: All {len(midi_data.instruments)} tracks are fully active.\n")
            
            # --- ENFORCE HIERARCHY: [genre]/[topic]/[title].mid ---
            def clean(s): return "".join(c for c in s if c.isalnum() or c in (' ', '_', '/')).replace(' ', '_').lower()
            
            safe_genre = clean(composition.meta.genre)
            safe_topic = clean(composition.meta.folder)
            safe_title = clean(composition.meta.title)
            
            # Build strict path
            final_dir = os.path.join(base_output, safe_genre, safe_topic)
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, f"{safe_title}_attempt{current_attempt}.mid")
            
            midi_data.write(final_path)
            print(f"Success! Song archived at: {final_path}")
            
            if args.render:
                try:
                    composer.render_to_audio(final_path)
                    print(f"\n[SERVER QA] PASSED: Remote audit and rendering successful.\n")
                    break
                except Exception as e:
                    error_str = str(e)
                    if "FINAL PRODUCTION AUDIT FAILED" in error_str and current_attempt < max_retries:
                        print(f"\n[SERVER QA] REJECTED BY BRIDGE: {error_str}")
                        print(f"[SERVER QA] Auto-correcting and maintaining context for Attempt {current_attempt + 1}...\n")
                        active_prompt = f"{full_concept}\n\nSERVER QA FEEDBACK (DO NOT REPEAT MISTAKE):\nThe rendering server rejected the previous MIDI file with this error: {error_str}. You MUST fix this."
                        current_attempt += 1
                        continue
                    else:
                        print(f"\n[SERVER QA] ERROR or Max Retries Reached: {error_str}")
                        break
            else:
                break

if __name__ == "__main__":
    main()
