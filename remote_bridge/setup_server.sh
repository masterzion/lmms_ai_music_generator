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

# 3. Install PyTorch (CUDA Optimized)
echo "Installing PyTorch with CUDA support..."
# This version is usually compatible with most modern 8GB cards
pip install torch --extra-index-url https://download.pytorch.org/whl/cu121

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
echo "--- Verification ---"
python3 -c "import torch; print(f'PyTorch Version: {torch.__version__}'); print(f'GPU Available: {torch.cuda.is_available()}'); print(f'GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo "--- Setup Complete ---"
echo "To start the server, run:"
echo "source venv/bin/activate && python server.py"
