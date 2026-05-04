#!/bin/bash

# ACE-Step Remote Bridge - Automated Setup Script
# Run this on your 192.168.2.188 (8GB VRAM) machine

echo "--- Starting ACE-Step Server Setup ---"

# Load local environment variables if they exist
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 1. Create Virtual Environment
echo "Creating virtual environment (venv)..."
python3 -m venv venv
source venv/bin/activate

# 2. Upgrade Pip
pip install --upgrade pip

# 3. Install PyTorch (ROCm Optimized for AMD / Steam Deck Python 3.13)
echo "Checking PyTorch installation..."
if python3 -c "import torch" 2>/dev/null; then
    echo "PyTorch is already installed. Skipping wheel downloads."
else
    echo "Installing PyTorch Nightly with ROCm support..."
    # Using wget for large wheels because it's more robust than pip for Steam Deck downloads
    TORCH_URL="https://download.pytorch.org/whl/nightly/rocm6.1/torch-2.6.0.dev20241223%2Brocm6.1-cp313-cp313-manylinux_2_28_x86_64.whl"
    TORCH_WHEEL="torch-2.6.0.dev20241223+rocm6.1-cp313-cp313-manylinux_2_28_x86_64.whl"

    TRITON_URL="https://download.pytorch.org/whl/nightly/rocm6.1/pytorch_triton_rocm-3.2.0%2Bgit0d4682f0-cp313-cp313-linux_x86_64.whl"
    TRITON_WHEEL="pytorch_triton_rocm-3.2.0+git0d4682f0-cp313-cp313-linux_x86_64.whl"

    if [ ! -f "$TORCH_WHEEL" ]; then
        echo "Downloading Torch wheel (2.7GB)..."
        wget -c "$TORCH_URL" -O "$TORCH_WHEEL"
    fi

    if [ ! -f "$TRITON_WHEEL" ]; then
        echo "Downloading Triton wheel (262MB)..."
        wget -c "$TRITON_URL" -O "$TRITON_WHEEL"
    fi

    echo "Installing local wheels..."
    pip install "$TRITON_WHEEL"
    pip install --pre "$TORCH_WHEEL" --extra-index-url https://download.pytorch.org/whl/nightly/rocm6.1
fi

echo "Installing remaining PyTorch components (torchvision, torchaudio)..."
pip install --pre torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.1

# 4. Install API Dependencies
echo "Installing API and utility dependencies..."
pip install -r requirements.txt

# 5. Download ACE-Step Weights
MODEL_URL="https://huggingface.co/ACE-Step/Ace-Step1.5/resolve/main/acestep-v15-turbo/model.safetensors"
MODEL_FILE="model.safetensors"
if [ ! -f "$MODEL_FILE" ]; then
    echo "Downloading ACE-Step 1.5 Turbo weights..."
    if [ -n "$HF_TOKEN" ]; then
        wget -c --header="Authorization: Bearer $HF_TOKEN" -O "$MODEL_FILE" "$MODEL_URL"
    else
        echo "Notice: HF_TOKEN not set. Attempting public download..."
        wget -c -O "$MODEL_FILE" "$MODEL_URL"
    fi
else
    echo "ACE-Step weights already found ($MODEL_FILE)."
fi

# 6. Verification Check
echo "--- Verification (Steam Deck Optimized) ---"
# Set overrides for verification to work on Deck
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export PYTORCH_ROCM_ARCH=gfx1030

python3 -c "import torch; print(f'PyTorch Version: {torch.__version__}'); print(f'ROCm/HIP Available: {getattr(torch.version, \"hip\", None) is not None}'); print(f'GPU Available: {torch.cuda.is_available()}'); print(f'GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}'); print(f'BFloat16 Supported: {torch.cuda.is_bf16_supported() if torch.cuda.is_available() else \"N/A\"}')"

echo "--- Setup Complete ---"
echo "To start the server on Steam Deck, run:"
echo "export HSA_OVERRIDE_GFX_VERSION=10.3.0 && source venv/bin/activate && python server.py"

# 7. --- AUDIO RENDERING ENGINE (CONTAINERIZED) ---
echo "--- Setting up Audio Rendering Engine (Podman/FluidSynth) ---"
if command -v podman >/dev/null 2>&1; then
    echo "Podman detected. Building ACE-Step Renderer image..."
    if [ -f "Dockerfile.renderer" ]; then
        podman build -t ace-step-renderer -f Dockerfile.renderer .
        echo "Renderer image built successfully."
    else
        echo "Error: Dockerfile.renderer not found. Skipping image build."
    fi
else
    echo "Notice: Podman not found. Containerized rendering will be unavailable."
    echo "To enable WAV rendering on Steam Deck, install Podman via Discover/Flatpak or system packages."
fi

echo "Checking for High-Fidelity Electronic SoundFont (SGM-V2.01)..."
mkdir -p soundfonts
if [ ! -f "soundfonts/SGM-V2.01.sf2" ]; then
    echo "Downloading SGM-V2.01.sf2 (236MB - Excellent for EDM/Bass)..."
    wget -c -L -O soundfonts/SGM-V2.01.sf2 "https://archive.org/download/SGM-V2.01/SGM-V2.01.sf2"
else
    echo "SoundFont already exists."
fi

echo "Setup Complete! ROCm is ready. Audio Rendering is optional."
