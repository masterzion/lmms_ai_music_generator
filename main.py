import os
import config
from core.parser import parse_prompt
from llm.prompt_expander import expand_prompt
from llm.planner import create_song_plan
from generators.melody import generate_melody
from generators.drums import generate_drums
from generators.bass import generate_bass
from generators.pads import generate_pads
from generators.chords import generate_chords
from core.midi_cleanup import cleanup_midi_clip
from core.assembly_engine import assemble_song
from renderers.midi_renderer import render_song
from renderers.wav_renderer import render_custom_wav

def generate_song(user_prompt, output_dir="outputs", topic_override=None):
    """
    Core pipeline to generate a full song from a single prompt.
    """
    genre, parsed_topic = parse_prompt(user_prompt)
    topic = topic_override if topic_override else parsed_topic
    print(f"--- Processing: {genre} | {topic} ---", flush=True)
    
    from core.style_config import STYLE_DATA
    style_info = STYLE_DATA.get(genre, STYLE_DATA["chillout"])
    genre_config = style_info["pipeline"]
    
    print("--- Step 1: Expanding prompt ---", flush=True)
    expanded = expand_prompt(genre, topic)
    print(f"SUCCESS: Expanded prompt received:\n{expanded[:500]}...", flush=True)

    print("--- Step 2: Creating song plan ---", flush=True)
    plan = create_song_plan(expanded, genre=genre)
    title = plan.get("title", "untitled").replace(" ", "_")
    bpm = plan.get("bpm", 130)
    key = plan.get("key", "C minor")
    print(f"SUCCESS: Plan created for '{title}'", flush=True)
    
    # Prepare output directory
    final_output_path = os.path.join(output_dir, genre, topic)
    os.makedirs(final_output_path, exist_ok=True)

    print("--- Step 3: Generating AI melody clips ---", flush=True)
    melody_clips = generate_melody(plan)
    
    print("--- Step 4: Cleaning up MIDI ---", flush=True)
    cleaned_clips = []
    for section_track_list in melody_clips:
        cleaned_section = [
            cleanup_midi_clip(c, bpm, key) if c else None for c in section_track_list
        ]
        cleaned_clips.append(cleaned_section)

    print("--- Step 5: Generating rhythm section ---", flush=True)
    drum_inst = generate_drums(plan, bpm, genre_config)
    bass_inst = generate_bass(plan, bpm, genre_config)
    pads_inst = generate_pads(plan, bpm, genre_config)
    print("  Generating chords (Pianos)...")
    piano_tracks = generate_chords(plan, bpm, genre_config, genre)

    print("--- Step 6: Assembling song ---")
    song = assemble_song(bpm, plan, cleaned_clips, drum_inst, bass_inst, pads_inst, piano_tracks)

    print("--- Step 7: Exporting ---", flush=True)
    midi_file = os.path.join(final_output_path, f"{title}.mid")
    wav_file = os.path.join(final_output_path, f"{title}.wav")
    
    song.write(midi_file)
    print(f"  MIDI saved to {midi_file}", flush=True)
    
    total_seconds = song.get_end_time()
    mins = int(total_seconds // 60)
    secs = int(total_seconds % 60)
    print(f"  Total Duration: {mins}:{secs:02d}", flush=True)

    render_custom_wav(midi_file, wav_file, genre=genre)
    
    print(f"--- Finished: {title} ---", flush=True)
    return midi_file, wav_file

def main():
    user_prompt = "<futurepop> create a song about neon dreams"
    generate_song(user_prompt)

if __name__ == "__main__":
    main()
