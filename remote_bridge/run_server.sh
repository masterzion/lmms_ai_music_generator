#!/bin/bash

# Steam Deck ROCm Override
# Load local environment variables if they exist
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

export HSA_OVERRIDE_GFX_VERSION=10.3.0
export PYTORCH_ROCM_ARCH=gfx1030
export PYTORCH_HIP_ALLOC_CONF="max_split_size_mb:128"

# Check for model weights
MODEL_FILE="model.safetensors"
if [ ! -f "$MODEL_FILE" ]; then
    echo "ACE-Step Bridge: ERROR - $MODEL_FILE not found."
    echo "Please run 'bash setup_server.sh' first."
    exit 1
fi

# Wait if a download is in progress (check if file is open for writing)
# We use fuser or lsof to check if the file is being written by wget
while fuser "$MODEL_FILE" >/dev/null 2>&1; do
    echo "ACE-Step Bridge: Waiting for $MODEL_FILE download to complete..."
    sleep 30
done

# Activate environment and run
echo "--- Starting ACE-Step Remote Bridge on Steam Deck ---"
echo "ACE-Step Bridge: Model allocation will begin before port is opened."
source venv/bin/activate
python server.py
