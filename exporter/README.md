# MIDI to LMMS Exporter

A Python utility to convert MIDI files into LMMS (`.mmp`) project files with intelligent track routing and custom plugin mapping.

## Requirements

The script requires **Python 3.x** and the **mido** library.
A virtual environment is already set up in this project with the necessary dependencies.

- **Python Library**: `mido`

## Installation

If you need to install the dependencies in a new environment:
```bash
pip install mido
```

## How to Run

Use the provided virtual environment to ensure all dependencies are met:

```bash
/media/master/ssd/music_maker/venv/bin/python midi_to_lmms.py <input_file.mid> [output_file.mmp]
```

### Example:
```bash
/media/master/ssd/music_maker/venv/bin/python midi_to_lmms.py sample.mid my_song.mmp
```

## Features

1. **Automatic Drum Routing**: 
   - Tracks containing "drum", "kick", "clap", "snare", "hihat", etc., in their name are automatically moved to the **Beat/Bassline Editor**.
   - Tracks on MIDI Channel 10 are also treated as drums.
   
2. **Interactive Plugin Selection**:
   - For melodic tracks, you will be prompted to choose a plugin:
     - **Sf2Player**: Standard LMMS SoundFont player.
     - **Vestige3**: Custom VST3 bridge (configured to use `/media/master/ssd/vts3/plugin/build/libvst3instrument_core.so`).
     - **AudioFileProcessor**: Standard sample player.
   - You can choose a global plugin for all tracks or decide track-by-track.

3. **Time Conversion**:
   - Converts MIDI ticks to LMMS PPQ (192) to maintain rhythm and duration accuracy.

## Project Structure

- `midi_to_lmms.py`: The main conversion script.
- `create_test_midi.py`: A helper script to generate a sample MIDI for testing.
- `README.md`: This documentation.
