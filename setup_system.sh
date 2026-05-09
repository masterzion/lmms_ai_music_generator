#!/bin/bash
set -e

# Ensure non-interactive mode for apt
export DEBIAN_FRONTEND=noninteractive

echo "Starting system setup for AI Music Maker..."

# 1. System Packages
echo "Detecting package manager..."
if command -v apt-get &> /dev/null; then
    echo "Installing system dependencies via apt..."
    sudo apt-get update && sudo apt-get install -y fluidsynth ffmpeg git python3-venv
elif command -v brew &> /dev/null; then
    echo "Installing system dependencies via brew..."
    brew install fluidsynth ffmpeg git
else
    echo "WARNING: Neither apt nor brew found. Please install fluidsynth, ffmpeg, and git manually."
fi

# 2. Project Directory Setup
mkdir -p outputs/midi_llm_tmp outputs/api_generated soundfonts

# 3. Soundfont Setup
SF_PATH="soundfonts/FluidR3_GM.sf2"
mkdir -p soundfonts

# Remove dead symlink if it exists
if [ -L "$SF_PATH" ] && [ ! -e "$SF_PATH" ]; then
    echo "Removing dead symlink: $SF_PATH"
    rm "$SF_PATH"
fi

if [ -f "$SF_PATH" ]; then
    echo "Found $SF_PATH, skipping download."
elif [ -f "/usr/share/sounds/sf2/FluidR3_GM.sf2" ]; then
    echo "Found FluidR3_GM.sf2 in system path, symlinking..."
    ln -sf /usr/share/sounds/sf2/FluidR3_GM.sf2 "$SF_PATH"
else
    echo "FluidR3_GM.sf2 not found. Downloading (142MB)..."
    curl -L -s -o "$SF_PATH" "https://github.com/pianobooster/fluid-soundfont/releases/download/v3.1/FluidR3_GM.sf2"
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

# Safely attempt to get the GPU vendor ID using lspci
GPU_VENDOR_ID=""
if command -v lspci &> /dev/null; then
    # Extract the 4-hex-digit vendor ID (e.g., 10de for NVIDIA, 1002 for AMD)
    GPU_VENDOR_ID=$(lspci -nn | grep -E -i "vga|3d|display" | grep -o '\[[0-9a-fA-F]\{4\}:' | head -n 1 | tr -d '[:]')
fi

# Check for manual CPU override
if [ "${FORCE_CPU}" == "1" ]; then
    echo "FORCE_CPU=1 detected. Defaulting to CPU mode."
# Check for NVIDIA GPU (Vendor ID: 10de)
elif [ "$GPU_VENDOR_ID" == "10de" ]; then
    echo "Detected NVIDIA GPU (Vendor ID: 10de)."
    if command -v nvidia-smi &> /dev/null; then
        VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
        if [ "$VRAM" -ge 4000 ]; then
            echo "NVIDIA GPU has ${VRAM}MB VRAM. Using CUDA mode."
            INSTALL_MODE="cuda"
            TORCH_URL="" # Use default index
        else
            echo "NVIDIA GPU VRAM (${VRAM}MB) is too low for LLMs. Defaulting to CPU."
        fi
    else
        echo "nvidia-smi not found. Defaulting to CPU mode as safety fallback."
    fi
# Check for AMD GPU (Vendor ID: 1002)
elif [ "$GPU_VENDOR_ID" == "1002" ]; then
    echo "Detected AMD GPU (Vendor ID: 1002). Treating as ROCm/Steam Deck environment."
    
    # Generate/Update .env file with Steam Deck specific overrides
    echo "Creating/Updating .env file with hardware overrides..."
    touch .env
    grep -q "HSA_OVERRIDE_GFX_VERSION" .env || echo "HSA_OVERRIDE_GFX_VERSION=10.3.0" >> .env
    grep -q "FORCE_CPU" .env || echo "FORCE_CPU=0" >> .env

    echo "Auto-configuring PyTorch ROCm nightly for Python 3.13 compatibility..."
    INSTALL_MODE="rocm"
    TORCH_URL="https://download.pytorch.org/whl/nightly/rocm6.2"
else
    echo "No supported dedicated GPU detected via lspci. Defaulting to CPU mode."
fi

echo "Installing Python dependencies in ${INSTALL_MODE} mode..."
source venv/bin/activate
pip install --upgrade pip

if [ "$INSTALL_MODE" == "cpu" ]; then
    # Use stable 2.6.0+cpu for Python 3.13
    pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url "$TORCH_URL"
else
    # Use nightly/pre-release for ROCm 6.2 + Python 3.13 compatibility
    pip install --pre torch torchvision torchaudio --index-url "$TORCH_URL" --extra-index-url https://pypi.org/simple
fi

# Ensure compatible numpy for numba
pip install "numpy<2.3"

# 6. MIDI-LLM Repository
echo "Cloning MIDI-LLM repository..."
git clone https://github.com/slSeanWU/MIDI-LLM


# 7. MIDI-LLM Dependencies
echo "Installing MIDI-LLM specific dependencies..."
# Create a filtered requirements file to avoid overwriting our ROCm/CPU torch and to skip NVIDIA-only bloat
FILTER_PATTERN="vllm|nvidia-|cupy-cuda|xformers|triton|torch==|torchvision==|torchaudio=="

if [ "$INSTALL_MODE" == "cpu" ]; then
    grep -vE "$FILTER_PATTERN" MIDI-LLM/requirements.txt > MIDI-LLM/requirements_filtered.txt
    pip install -r MIDI-LLM/requirements_filtered.txt
elif [ "$INSTALL_MODE" == "rocm" ]; then
    # For ROCm, we also want to avoid standard CUDA-linked packages
    grep -vE "$FILTER_PATTERN" MIDI-LLM/requirements.txt > MIDI-LLM/requirements_filtered.txt
    pip install -r MIDI-LLM/requirements_filtered.txt
else
    pip install -r MIDI-LLM/requirements.txt
fi

# 8. Model Download (Optional)
echo ""
echo "-------------------------------------------------------"
echo "8. MODEL DOWNLOAD"
echo "-------------------------------------------------------"
echo "The MIDI-LLM model is approximately 3.5GB."

# Default to 'y' for non-interactive behavior unless explicitly disabled
if [ "${AUTO_DOWNLOAD}" == "0" ]; then
    echo "AUTO_DOWNLOAD=0 detected. Skipping download."
    download_confirm="n"
elif [ "${AUTO_DOWNLOAD}" == "1" ] || [ ! -t 0 ]; then
    echo "Non-interactive mode or AUTO_DOWNLOAD=1. Automatically starting download..."
    download_confirm="y"
else
    read -p "Would you like to download it now? (y/n): " download_confirm
fi

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
