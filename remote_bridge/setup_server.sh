#!/bin/bash

# ACE-Step Remote Bridge - Automated Setup Script
# Run this on your 192.168.2.188 (8GB VRAM) machine

echo "--- Starting ACE-Step Server Setup ---"

# 1. Create Virtual Environment
echo "Creating virtual environment (venv)..."
python3 -m venv venv
source venv/bin/activate

# 2. Upgrade Pip
pip install --upgrade pip

# 3. Install PyTorch (ROCm Optimized for AMD / Steam Deck Python 3.13)
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

echo "Installing remaining PyTorch components (torchvision, torchaudio)..."
pip install --pre torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.1

# 4. Install API Dependencies
echo "Installing API and utility dependencies..."
pip install -r requirements.txt

# 5. Download ACE-Step Weights (Placeholder)
# Replace the URL below with your actual model source
MODEL_URL="https://huggingface.co/ace-step/ACE-Step-1.5/resolve/main/ace_step_1.5.pt"
if [ ! -f "ace_step_1.5.pt" ]; then
    echo "Downloading ACE-Step 1.5 weights..."
    # wget -O ace_step_1.5.pt $MODEL_URL
    echo "NOTICE: Please manually download ace_step_1.5.pt to this folder."
else
    echo "ACE-Step weights already found."
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
