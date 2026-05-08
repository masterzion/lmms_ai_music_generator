#!/bin/bash
set -e

echo "Starting system setup for AI Music Maker..."

# 1. System Packages
echo "Detecting package manager..."
if command -v apt-get &> /dev/null; then
    echo "Installing system dependencies via apt..."
    sudo apt update && sudo apt install -y fluidsynth ffmpeg git python3-venv
elif command -v brew &> /dev/null; then
    echo "Installing system dependencies via brew..."
    brew install fluidsynth ffmpeg git
else
    echo "WARNING: Neither apt nor brew found. Please install fluidsynth, ffmpeg, and git manually."
fi

# 2. Project Directory Setup
mkdir -p outputs/midi_llm_tmp outputs/api_generated soundfonts

# 3. Soundfont Setup
if [ -f "/usr/share/sounds/sf2/FluidR3_GM.sf2" ]; then
    echo "Found FluidR3_GM.sf2, symlinking..."
    ln -sf /usr/share/sounds/sf2/FluidR3_GM.sf2 soundfonts/FluidR3_GM.sf2
else
    echo "WARNING: FluidR3_GM.sf2 not found in /usr/share/sounds/sf2/."
    echo "You may need to download it manually to soundfonts/FluidR3_GM.sf2"
fi

# 4. Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 5. Python Packages
echo "Installing Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install pretty_midi mido pydantic requests numpy fastapi uvicorn midi2audio torch transformers accelerate

# 6. MIDI-LLM Repository
if [ ! -d "MIDI-LLM" ]; then
    echo "Cloning MIDI-LLM repository..."
    git clone https://github.com/slSeanWU/MIDI-LLM
fi

# 7. MIDI-LLM Dependencies (including anticipation)
echo "Installing MIDI-LLM specific dependencies..."
./venv/bin/pip install -r MIDI-LLM/requirements.txt

echo "Setup Complete!"
echo "To start the MIDI-LLM API server: ./venv/bin/python midi_llm_api.py"
echo "To generate a song: ./venv/bin/python main.py"
