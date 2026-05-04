# ACE-Step Remote Bridge

This server is designed to run on a machine with **8 GB VRAM** (e.g., `192.168.2.188`). It provides a high-performance API for generating musical patterns using PyTorch and ACE-Step logic.

## Setup Instructions

1.  **Transfer this folder** to your 8 GB VRAM machine.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the server**:
    ```bash
    python server.py
    ```
    The server will start on `http://0.0.0.0:8000`.

## API Endpoints

### `POST /generate_pattern`
Generates a musical motif based on a prompt and energy level.

**Payload**:
```json
{
  "prompt": "Dark EBM bassline",
  "genre": "EBM",
  "energy": 0.9
}
```

## Integration with Composer
Once this server is running, you can update your local `composer.py` to fetch specialized patterns from this API.
