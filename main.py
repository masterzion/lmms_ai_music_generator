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

    print(f"--- Creative Director & Librarian: Starting session for '{args.concept}' ---")
    composer = Composer(model_name=args.model)
    
    try:
        composition = composer.compose(full_concept)
    except Exception as e:
        print(f"Failed to generate composition: {e}")
        return

    if composition:
        print(f"Librarian: Sorting '{composition.meta.title}' into {composition.meta.genre}/{composition.meta.folder}")
        
        engine = SequencerEngine(composition)
        midi_data = engine.generate()
        
        # --- ENFORCE HIERARCHY: [genre]/[topic]/[title].mid ---
        def clean(s): return "".join(c for c in s if c.isalnum() or c in (' ', '_', '/')).replace(' ', '_').lower()
        
        safe_genre = clean(composition.meta.genre)
        safe_topic = clean(composition.meta.folder)
        safe_title = clean(composition.meta.title)
        
        # Build strict path
        final_dir = os.path.join(base_output, safe_genre, safe_topic)
        os.makedirs(final_dir, exist_ok=True)
        final_path = os.path.join(final_dir, f"{safe_title}.mid")
        
        midi_data.write(final_path)
        print(f"Success! Song archived at: {final_path}")

if __name__ == "__main__":
    main()
