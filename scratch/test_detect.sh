#!/bin/bash
if command -v nvidia-smi &> /dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
    echo "VRAM is: $VRAM"
    if [ "$VRAM" -ge 4000 ]; then
        echo "CUDA"
    else
        echo "CPU (VRAM too low)"
    fi
else
    echo "CPU (No NVIDIA)"
fi
