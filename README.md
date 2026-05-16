# Professional AI Music Generator Documentation

This repository contains a genre-aware AI music generation pipeline. It uses **NotaGen** (a hierarchical GPT-2 symbolic music model) for melodic tracks, a deterministic rule-based engine for drum/percussion tracks, and an Ollama LLM for song planning and structure. The API server and Batch Client work together for automated, multi-track MIDI production.

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Batch Client (api_batch_client.py)                          │
│  Reads songs_to_generate.txt → requests plan → requests MIDI │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (port 9000)
┌───────────────────────────▼─────────────────────────────────┐
│  API Server (midi_llm_api.py)                                │
│  ├── /generate_full   → Ollama LLM → JSON song plan          │
│  ├── /generate_from_plan → NotaGen + Drum Generator → MIDI   │
│  ├── /convert         → FluidSynth → WAV                     │
│  └── /download        → file download                        │
└──────┬──────────────────────┬───────────────────────────────┘
       │                      │
┌──────▼──────┐   ┌───────────▼──────────┐
│  NotaGen    │   │  Drum Generator       │
│  (notagen/  │   │  (notagen/            │
│  notagen_   │   │  drum_generator.py)   │
│  backend.py)│   │  Rule-based, poly=1   │
│  110M params│   │  guaranteed           │
│  CPU only   │   └──────────────────────┘
└──────┬──────┘
       │ ABC notation
┌──────▼──────────────────────┐
│  abc_to_midi.py              │
│  Deterministic polyphony     │
│  enforcement + MIDI write    │
└─────────────────────────────┘
```

---

## 2. Prerequisites

### System packages
```bash
# FluidSynth (for WAV rendering)
sudo apt install fluidsynth

# abc2midi (optional — used by abctoolkit)
sudo apt install abcmidi
```

### Python environment
```bash
# Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt
pip install music21 abctoolkit==0.0.6 samplings==0.1.7
```

### External services
- **Ollama** running at the URL configured in `config.py` → `OLLAMA_API_BASE`
  - Required model: whichever model your `llm/planner.py` references (e.g. `mistral`, `llama3`)

---

## 3. First-Time Model Setup

The NotaGen-small model weights (~1.32 GB) are downloaded automatically on first startup if not present. To pre-download manually:

```bash
source venv/bin/activate
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='ElectricAlexis/NotaGen',
    filename='weights_notagen_pretrain_p_size_16_p_length_2048_p_layers_12_c_layers_3_h_size_768_lr_0.0002_batch_8.pth',
    local_dir='models/NotaGen-small'
)
print('Done.')
"
```

The NotaGen source code is bundled at `NotaGen-repo/` (cloned from GitHub). No additional setup is needed for it.

---

## 4. Running the API Server

```bash
source venv/bin/activate
python3 midi_llm_api.py
```

The server starts on **port 9000**. On startup it:
1. Detects AMD/GPU hardware and applies overrides if needed
2. Loads NotaGen-small (110M params, ~1.5 GB RAM) onto CPU
3. Restores all project config cleanly (Ollama URL, output paths, etc.)

Expected startup output:
```
Loading NotaGen-small model from 'models/NotaGen-small'...
  [NotaGen] Model parameters: 109,579,776
  [NotaGen] Model loaded on CPU.
NotaGen model loaded successfully!
INFO:     Uvicorn running on http://0.0.0.0:9000
```

### Environment overrides
| Variable | Default | Description |
|---|---|---|
| `NOTAGEN_MODEL_PATH` | `models/NotaGen-small` | Path to weights directory |
| `MAX_PARALLEL_TRACKS` | `2` | Reserved (generation is sequential on CPU) |
| `PIPEWIRE_LOG_LEVEL` | `0` | Suppresses FluidSynth audio warnings |

---

## 5. API Endpoints

### `POST /generate_full`
Plans a full song from a natural language prompt. Calls the Ollama LLM.
```bash
curl -X POST http://localhost:9000/generate_full \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "<ebm> Black Market Memories"}'
```
Returns: `{"status": "success", "genre": "ebm", "topic": "...", "plan": {...}}`

### `POST /generate_from_plan`
Generates all MIDI tracks from a JSON plan (produced by `/generate_full`).
- Melodic tracks → NotaGen ABC generation → deterministic polyphony enforcement
- Drum/percussion tracks → rule-based pattern generator (polyphony = 1, always)
- All tracks merged into one multi-track `.mid` file
```bash
curl -X POST http://localhost:9000/generate_from_plan \
  -H "Content-Type: application/json" \
  -d '{"plan": <plan_json>}'
```
Returns: `{"status": "success", "midi_path": "...", "track_count": N}`

### `POST /generate`
Test endpoint — generate a single 8-bar MIDI clip from a raw NotaGen prompt.
```bash
curl -X POST http://localhost:9000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Romantic|Chopin, Frédéric|solo piano"}'
```
Prompt format: `"Period|Composer|Instrumentation"`

### `POST /convert`
Render a MIDI file to WAV using FluidSynth.
```bash
curl -X POST http://localhost:9000/convert \
  -H "Content-Type: application/json" \
  -d '{"midi_path": "outputs/api_generated/mysong_merged.mid"}'
```

### `GET /download`
Download any generated file by server path.
```bash
curl "http://localhost:9000/download?path=outputs/api_generated/mysong_merged.mid" \
  -o mysong.mid
```

---

## 6. Running the Batch Client

The batch client automates mass production from a playlist file. The API server **must be running** first.

```bash
source venv/bin/activate
python3 batch_client/api_batch_client.py --file batch_client/songs_to_generate.txt
```

To filter by genre:
```bash
python3 batch_client/api_batch_client.py --file batch_client/songs_to_generate.txt --type ebm
```

### Playlist file format (`songs_to_generate.txt`)
```
<genre>: <topic>: <natural language prompt>
```
Example:
```
<ebm>: Black Market Memories: Dark industrial groove with pounding bass and mechanical drums
<futurepop>: Neon Dreams: Uplifting anthem with super-saw leads and emotional chord progressions
```

Output files are saved to `batch_client/outputs/<genre>/<topic>/`.

---

## 7. Exporter (LMMS Integration)

Convert any generated MIDI into an LMMS project:
```bash
source venv/bin/activate
python3 exporter/midi_to_lmms.py <path_to_midi_file>
```

- **Drums/Claps/Snares** → Beat/Baseline Editor (automatic detection)
- **Instrument tracks** → SF2 player or VST3 (configurable)

---

## 8. Configuration

### `config.py`
| Key | Description |
|---|---|
| `MIDI_LLM_API_BASE` | URL of the API server (default: `http://127.0.0.1:9000`) |
| `OLLAMA_API_BASE` | URL of your Ollama instance |
| `OUTPUT_DIR` | Root directory for all generated files |
| `SOUNDFONT_PATH` | Path to the GM soundfont for FluidSynth rendering |

### `core/style_config.py`
All genre-level parameters — polyphony limits, BPM ranges, section densities, track counts, humanization. These flow automatically into every generation request via the API.

### `core/structures.py`
Song structure templates per genre (section names, ordering patterns).

---

## 9. Polyphony Guarantee

Unlike the previous MIDI-LLM backend (which used a logits processor that could still fail after 12 attempts), polyphony is now **100% deterministically enforced**:

- **Drum tracks**: Rule-based generator never exceeds 1 simultaneous note by construction.
- **Melodic tracks**: After ABC→MIDI conversion, a Python sort-and-slice enforces the limit. Mathematically impossible to violate.

The API logs a full polyphony audit after every `/generate_from_plan` call:
```
[API] Polyphony Audit:
  ✓ Clap: 1/1 simultaneous notes
  ✓ Bass: 2/4 simultaneous notes
  ✓ Lead: 3/4 simultaneous notes
```

---

## 10. Hardware Notes

| Setup | Behaviour |
|---|---|
| **CPU only** (default) | NotaGen runs in `float32`. ~2–5 min per melodic track on a 4-core CPU. |
| **AMD GPU** | Hardware detected automatically; `HSA_OVERRIDE_GFX_VERSION=10.3.0` applied. |
| **RAM requirement** | ~2 GB for NotaGen-small. 8 GB total system RAM minimum recommended. |

> NotaGen-small (110M params) was chosen specifically for CPU viability on a 12 GB RAM / 4-core system.
> NotaGen-medium (244M) or NotaGen-large (516M) can be used by changing `size="small"` to `size="medium"/"large"` in the lifespan loader and pointing `NOTAGEN_MODEL_PATH` to the corresponding weights file.

---

## 11. Development Notes

- `NotaGen-repo/` — cloned GitHub source for the NotaGen model classes. Do not modify.
- `notagen/` — integration layer: backend, ABC→MIDI converter, drum generator.
- `MIDI-LLM/` — legacy backend, no longer used by the API. Kept for reference.
- **Branches**: Use `new_version` for the latest features.
- **Git ignores**: `outputs/`, `models/`, `*.mid`, `*.wav`, `NotaGen-repo/` are excluded from tracking.
