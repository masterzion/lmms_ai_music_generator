# ACE-Step Remote Bridge (Steam Deck Optimized)

This server is optimized to run on the **Steam Deck** (or machines with 8GB+ VRAM/Shared Memory) using **ROCm**. It provides a high-performance API for generating musical patterns and full compositions using ACE-Step logic.

## Setup Instructions

1.  **Run the setup script**:
    ```bash
    bash setup_server.sh
    ```
    This script handles the virtual environment, installs ROCm-optimized PyTorch, downloads the model weights, and builds the containerized audio renderer.

2.  **Run the server**:
    ```bash
    bash run_server.sh
    ```
    The server will start on `http://0.0.0.0:8000`.

## Audio Rendering (WAV)

WAV rendering is handled via **Podman** to bypass the Steam Deck's read-only filesystem limitations.
- Requirement: `podman` must be installed on the host.
- Method: The server launches a temporary Alpine-based container with `fluidsynth` to process MIDI files using the `FluidR3_GM.sf2` SoundFont.

## API Endpoints

### `POST /generate_full_composition`
Generates a complete 160-bar MIDI arrangement with 10 tracks.

### `POST /render_wav`
Converts the last generated MIDI into a high-quality WAV file.

### `POST /generate_pattern`
Generates a specific musical motif based on a prompt.

## Integration with Composer/LMMS
The server returns MIDI files that can be directly imported into **LMMS** or any DAW. The `/render_wav` endpoint provides a quick "production preview" of the composition.
