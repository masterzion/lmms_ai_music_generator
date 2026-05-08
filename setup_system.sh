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

# 5. Hardware Detection & Python Packages
echo "Detecting hardware for optimal PyTorch installation..."

INSTALL_MODE="cpu"
TORCH_URL="https://download.pytorch.org/whl/cpu"

# Check for NVIDIA GPU with at least 4GB VRAM
if command -v nvidia-smi &> /dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
    if [ "$VRAM" -ge 4000 ]; then
        echo "Detected NVIDIA GPU with ${VRAM}MB VRAM. Using CUDA mode."
        INSTALL_MODE="cuda"
        TORCH_URL="" # Use default index
    else
        echo "Detected NVIDIA GPU but VRAM (${VRAM}MB) is too low for LLMs. Defaulting to CPU."
    fi
# Check for AMD GPU (ROCm)
elif [ -d "/opt/rocm" ] || command -v rocm-smi &> /dev/null; then
    echo "Detected AMD GPU/ROCm environment. Using ROCm mode."
    INSTALL_MODE="rocm"
    TORCH_URL="https://download.pytorch.org/whl/rocm6.0" # Adjust version as needed
fi

echo "Installing Python dependencies in ${INSTALL_MODE} mode..."
./venv/bin/pip install --upgrade pip

if [ "$INSTALL_MODE" == "cpu" ]; then
    ./venv/bin/pip install torch torchvision torchaudio --index-url "$TORCH_URL"
else
    ./venv/bin/pip install torch torchvision torchaudio ${TORCH_URL:+--index-url "$TORCH_URL"}
fi

./venv/bin/pip install pretty_midi mido pydantic requests numpy fastapi uvicorn midi2audio transformers accelerate

# 6. MIDI-LLM Repository
if [ ! -d "MIDI-LLM" ]; then
    echo "Cloning MIDI-LLM repository..."
    git clone https://github.com/slSeanWU/MIDI-LLM
fi

# 7. MIDI-LLM Dependencies (excluding heavy GPU-only bloat if on CPU)
echo "Installing MIDI-LLM specific dependencies..."
if [ "$INSTALL_MODE" == "cpu" ]; then
    # Filter out vllm and nvidia-specific packages from requirements
    grep -vE "vllm|nvidia-|triton" MIDI-LLM/requirements.txt > MIDI-LLM/requirements_cpu.txt
    ./venv/bin/pip install -r MIDI-LLM/requirements_cpu.txt
else
    ./venv/bin/pip install -r MIDI-LLM/requirements.txt
fi

# 8. Model Download (Optional)
echo ""
echo "-------------------------------------------------------"
echo "8. MODEL DOWNLOAD"
echo "-------------------------------------------------------"
echo "The MIDI-LLM model is approximately 3.5GB."
read -p "Would you like to download it now? (y/n): " download_confirm
if [[ "$download_confirm" =~ ^[Yy]$ ]]; then
    echo "Starting download..."
    ./venv/bin/python download_model.py
else
    echo "Skipping download. You can download it later by running: ./venv/bin/python download_model.py"
fi

echo ""
echo "Setup Complete!"
echo "To start the MIDI-LLM API server: ./venv/bin/python midi_llm_api.py"
echo "To generate a song: ./venv/bin/python main.py"
