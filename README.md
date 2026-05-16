# Professional AI Music Generator: Orpheus Edition

This repository contains a state-of-the-art, genre-aware symbolic music generation pipeline. It leverages the **Orpheus-Large (748M)** Music Transformer for deep, atmospheric, and aggressive multi-instrumental MIDI production. The system is specifically hardened for dark genres like **EBM**, **Industrial**, and **Dark-Techno**.

## 1. System Architecture

```mermaid
graph TD
    A[Batch Client] -- "JSON Plan Request" --> B[API Server]
    B -- "Section + Genre" --> C[Ollama LLM Planner]
    C -- "Song Plan (JSON)" --> B
    B -- "Seed Token (e.g. D#0)" --> D[Orpheus-Large Engine]
    D -- "3-Token MIDI Sequence" --> E[MIDI Decoder]
    E -- "Track Merging" --> F[Final MIDI File]
    F -- "FluidSynth" --> G[Audio Preview (WAV)]
```

## 2. The Engine: Orpheus-Large (748M)

The primary generative engine is an autoregressive Transformer decoder trained on over 2.3 million high-quality MIDI tracks.

- **Parameters**: 748 Million (Full Precision FP32).
- **Context Window**: 8,192 tokens (Enables long-form structural coherence).
- **Architecture**: Rotary Positional Embeddings (RoPE) + Flash Attention.
- **Encoding**: Specialized 3-token-per-note system: `[Time-shift, Pitch, Velocity/Duration]`.

## 3. Prerequisites

### System Packages
```bash
# FluidSynth (for high-quality WAV rendering)
sudo apt install fluidsynth ffmpeg
```

### Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install torch transformers pretty_midi mido
```

### Hardware Requirements
- **RAM**: 12GB Minimum (Model weights take ~2.8GB).
- **Storage**: ~3GB for model weights.
- **CPU**: Multicore recommended for parallel track rendering.

### Manual Model Download
If the model weights are missing, you can download them manually using `curl`:

```bash
mkdir -p models/Orpheus-Large
curl -L https://huggingface.co/asigalov61/Orpheus-Music-Transformer/resolve/main/Orpheus_Large_748M_2048_16_24_1536_32768_p_size_1_p_length_32768_p_layers_1_lr_0.0001_batch_1.pth -o models/Orpheus-Large/orpheus_large.pth
```

## 4. Running the System

### Start the API Server
```bash
source venv/bin/activate
python3 midi_llm_api.py
```
The server will initialize the **Orpheus-Large** model on your GPU (if available) or CPU.

### Run a Batch Generation
```bash
python3 batch_client/api_batch_client.py --file batch_client/songs_to_generate.txt
```

## 5. API Reference (Port 9000)

### `POST /generate_full`
Creates a complete song architecture (BPM, Key, Sections, Instruments) using the LLM Planner.
- **Input**: `{"user_prompt": "Dark Industrial EBM"}`

### `POST /generate_from_plan`
The core engine. Generates MIDI tokens for every track in the plan and merges them into a single file.
- **Engine**: Orpheus-Large 748M.
- **Note**: For dark genres, the engine is automatically "seeded" with low-register dissonant notes.

### `POST /convert`
Renders a MIDI file to high-fidelity WAV using the **FluidR3_GM** soundfont.

## 6. Project Structure

- `midi_llm_api.py`: The FastAPI gateway and track merging logic.
- `orpheus_backend.py`: The Transformer architecture and MIDI tokenization bridge.
- `llm/planner.py`: Genre-aware song structure architect.
- `core/style_config.py`: Personality settings (aggression, density, velocity).
- `batch_client/`: Automated mass-generation client.

## 7. Model Branching
- **Branch: `notagen`**: Legacy ABC-based system.
- **Branch: `MIDI-LLM_Llama-3.2-1B`**: Current cutting-edge Orpheus Transformer setup.

---
*Developed for professional-grade EBM and Industrial music production.*
