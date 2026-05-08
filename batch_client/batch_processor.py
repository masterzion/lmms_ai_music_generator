import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import generate_song

def run_batch(input_file):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r") as f:
        lines = f.readlines()

    print(f"Starting batch process for {len(lines)} songs...")

    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue
        
        # Split by : (genre:topic:prompt)
        parts = line.split(":", 2)
        if len(parts) < 3:
            print(f"Skipping invalid line: {line}")
            continue
            
        genre = parts[0].strip()
        topic = parts[1].strip()
        prompt_text = parts[2].strip()
        
        # Format the prompt as expected by our parser
        full_prompt = f"<{genre}> {prompt_text}"
        
        print(f"\n" + "="*50)
        print(f"BATCH JOB: {genre.upper()} | {topic.upper()}")
        print(f"PROMPT: {prompt_text}")
        print("="*50 + "\n", flush=True)

        # Save into the batch_client/outputs folder as requested
        client_output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        
        try:
            generate_song(full_prompt, output_dir=client_output_dir, topic_override=topic)
        except Exception as e:
            print(f"ERROR processing '{line}': {e}", flush=True)

if __name__ == "__main__":
    input_file = os.path.join(os.path.dirname(__file__), "songs_to_generate.txt")
    run_batch(input_file)
