# Professional AI Music Generator Documentation

This repository contains a high-end, genre-aware AI music generation pipeline. It supports distributed processing using a FastAPI server (for MIDI generation) and a Batch Client (for automated song production).

## 1. System Architecture

The system is divided into four main layers:
- **API (Server)**: Orchestrates the LLM and deterministic generators.
- **Batch Client**: Handles mass production and research-backed prompt expansion.
- **Generators**: Style-specific MIDI engines (Drums, Bass, Pianos, Pads).
- **Exporter**: Converts final MIDI files into LMMS projects (.mmpz).

---

## 2. The API (FastAPI)

The API is the central hub for generating songs.

### Running the API
```bash
uvicorn midi_llm_api:app --host 0.0.0.0 --port 8000
```

### Endpoints
- **POST `/generate`**: Main generation endpoint.
  - **Body**: `{ "prompt": "genre:topic Prompt text" }`
  - **Returns**: A high-density MIDI file.

---

## 3. The Batch Client (Mass Production)

The batch client automates the production of multiple songs based on a list.

### Usage
1. Edit `batch_client/songs_to_generate.txt` with your desired songs (format: `genre:topic:prompt`).
2. Run the processor:
   ```bash
   python batch_client/batch_processor.py
   ```

### Key Features
- **Dynamic Pacing**: Automatically adjusts bar counts (4:00 - 6:30 min).
- **Universal Drops**: Implements random section-level drops for all tracks.
- **One-Time Drops**: Ensures each instrument only "drops out" once per song.

---

## 4. Generative Engines (High-End Logic)

### Style Secrets
- **EBM**: 16th-note driving bass with octave jumps and dissonant piano solos.
- **Futurepop**: Sidechained "pumping" bass and anthem-like super-saw arpeggios.
- **Chillout**: Open Jazz voicings (Drop-2), 9th/11th extensions, and sparse motifs.

### Humanization
The system automatically applies +/- 7.5ms micro-timing jitter and velocity fluctuations to make the MIDI feel like a professional human performance.

---

## 5. Exporter (LMMS Integration)

The exporter allows you to move your AI-generated MIDI into a professional DAW (LMMS).

### Usage
```bash
python exporter/midi_to_lmms.py --input path/to/song.mid --output path/to/project.mmpz
```

### Routing
- **Drums/Percussion**: Automatically routed to the Beat/Baseline Editor.
- **Instrument Tracks**: Automatically assigned to SF2 or VST3 players based on configuration.

---

## 6. Command Line Tools

- **`download_model.py`**: Downloads the 4GB MIDI-LLM model with parallel threading (8 workers).
- **`analyze_midi.py`**: Provides a detailed breakdown of tracks and note counts for any generated file.
- **`setup_system.sh`**: One-click installer for all dependencies and virtual environments.

---

## 7. Configuration (`config.py`)

The `config.py` file is the brain of the system, controlling the "Production Standards" for every genre.

### Global Settings
- **`MIDI_LLM_API_BASE`**: The URL of your local or remote MIDI-LLM server.
- **`OLLAMA_API_BASE`**: The URL of your Ollama server.

### Genre Parameters
Each genre has a dedicated configuration block:
- **`bpm`**: The valid tempo range for the genre.
- **`min_tracks` / `max_tracks`**: Mandatory track counts for a professional "Wall of Sound."
- **`min_bars` / `max_bars`**: Enforces the 4:00 - 6:30 minute duration window.
- **`minor_only`**: Forces the generator to use minor scales (Essential for EBM).
- **`melody_density`**: Controls how many notes the AI melody generator produces (0.1 to 1.0).
- **`drum_density`**: Controls the complexity of the drum patterns.
- **`humanization`**: The base level of timing/velocity jitter applied before the cleanup stage.
- **`bass_repetition`**: Controls how often the bass pattern repeats vs. evolves.

---

## 8. Development & Git
- **Branches**: Use the `new_version` branch for the latest high-end features.
- **Ignoring Binaries**: The project is configured to ignore `**/outputs/`, `models/`, and all `*.mid`/`*.wav` files to keep the repository lightweight.
