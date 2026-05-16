"""
NotaGen backend: loads the real NotaGen model (custom hierarchical GPT-2)
and generates ABC notation from structured track metadata, then converts to MIDI.

Architecture:
  - PatchLevelDecoder  (GPT-2, generates patch-level features)
  - CharLevelDecoder   (GPT-2, generates chars within each patch)
  - Patchilizer        (custom tokenizer that encodes ABC text into patches)

Model weights: .pth file (NOT a standard HuggingFace checkpoint)

Source code from: https://github.com/ElectricAlexis/NotaGen
"""

import os
import sys
import time
import glob
import torch
import re
from pathlib import Path
from typing import Optional, List, Dict

# ── Add the cloned NotaGen inference directory to the path ──────────────────
# IMPORTANT: Use append (not insert) so the project root's config.py takes
# precedence over NotaGen-repo/inference/config.py in normal imports.
NOTAGEN_REPO = Path(__file__).parent.parent / "NotaGen-repo" / "inference"
if str(NOTAGEN_REPO) not in sys.path:
    sys.path.append(str(NOTAGEN_REPO))

# These are imported from the NotaGen repo
# They rely on PATCH_SIZE, PATCH_LENGTH, HIDDEN_SIZE etc. from config.py
# We monkey-patch the config before importing utils.

# ── Config constants per model size ─────────────────────────────────────────
# NotaGen-small (110M):  p_layers=12, c_layers=3, h_size=768,  p_length=2048
# NotaGen-medium (244M): p_layers=16, c_layers=3, h_size=1024, p_length=2048
# NotaGen-large (516M):  p_layers=20, c_layers=6, h_size=1280, p_length=1024
MODEL_CONFIGS = {
    "small":  dict(PATCH_NUM_LAYERS=12, CHAR_NUM_LAYERS=3, HIDDEN_SIZE=768,  PATCH_LENGTH=2048),
    "medium": dict(PATCH_NUM_LAYERS=16, CHAR_NUM_LAYERS=3, HIDDEN_SIZE=1024, PATCH_LENGTH=2048),
    "large":  dict(PATCH_NUM_LAYERS=20, CHAR_NUM_LAYERS=6, HIDDEN_SIZE=1280, PATCH_LENGTH=1024),
}

PATCH_SIZE   = 16   # constant across all sizes
PATCH_STREAM = True

# Default weights filename for NotaGen-small
_SMALL_WEIGHTS = (
    "weights_notagen_pretrain_p_size_16_p_length_2048"
    "_p_layers_12_c_layers_3_h_size_768_lr_0.0002_batch_8.pth"
)

# ── Prompt translation: plan metadata → NotaGen metadata prompt ─────────────

_INSTRUMENTATION_MAP = [
    (["bass synth", "bass line", "synth bass", "sub bass", "bass"], "Keyboard"),
    (["lead synth", "melody", "lead", "solo", "pluck"],             "Keyboard"),
    (["pad", "atmosphere", "ambient", "string", "choir", "choral"], "Ensemble"),
    (["arp", "sequence", "arpegg", "ostinato", "riff"],             "Keyboard"),
    (["stab", "chord", "harmonic"],                                 "Keyboard"),
    ([],                                                             "Ensemble"),
]

def _map_period(bpm: float, section_name: str, style_desc: str) -> str:
    combined = f"{section_name} {style_desc}".lower()
    if bpm >= 120 or any(w in combined for w in ["techno", "ebm", "industrial", "mechanical", "electronic"]):
        return "Contemporary"
    if any(w in combined for w in ["dark", "groove", "futurepop"]):
        return "Modern"
    return "Classical"

def _map_composer(period: str, style_desc: str, section_name: str) -> str:
    combined = f"{style_desc} {section_name}".lower()
    if period == "Contemporary" or any(w in combined for w in ["techno", "ebm", "electronic"]):
        return "Glass, Philip"  # Mechanical and repetitive
    if period == "Modern":
        return "Shostakovich, Dmitri" # Dramatic and rhythmic
    return "Mozart, Wolfgang Amadeus"

def _map_instrumentation(style_desc: str, instrument_name: str) -> str:
    combined = f"{instrument_name} {style_desc}".lower()
    for (keywords, result) in _INSTRUMENTATION_MAP:
        if not keywords:
            return result
        for kw in keywords:
            if kw in combined:
                return result
    return "Chamber"

def build_notagen_prompt(style_desc: str, instrument_name: str,
                         bpm: float, section_name: str) -> str:
    """Build the NotaGen metadata header lines."""
    period = _map_period(bpm, section_name, style_desc)
    composer = _map_composer(period, style_desc, section_name)
    instrumentation = _map_instrumentation(style_desc, instrument_name)
    
    # ── Medium Model Enrichment ──────────────────────────────────────────────
    # For Medium/Large models, we can add extra descriptive tags to the
    # instrumentation string to guide the style even further.
    style_lower = style_desc.lower()
    tags = []
    if "industrial" in style_lower or "ebm" in style_lower: 
        tags.append("Industrial")
        tags.append("Dissonant Minor 2nd")
        tags.append("Tritones")
        tags.append("Atonal")
    if "minimal" in style_lower:    tags.append("Minimal")
    if "driving" in style_lower:    tags.append("Driving")
    if "dark" in style_lower:       tags.append("Dark")
    
    if tags:
        tag_str = ", ".join(tags)
        instrumentation = f"{instrumentation} ({tag_str})"
    # ──────────────────────────────────────────────────────────────────────────

    return f"{period}|{composer}|{instrumentation}"


# ── Model loader ─────────────────────────────────────────────────────────────

def _inject_config(size: str = "small"):
    """
    Temporarily monkey-patch 'config' so NotaGen's utils.py can import it.
    Returns (cfg_dict, original_config_module_or_None).
    """
    import types
    cfg = MODEL_CONFIGS[size]

    # Save whatever was in sys.modules["config"] before (the project's config.py)
    original_config = sys.modules.get("config", None)

    # Build a fake config module for NotaGen
    config_mod = types.ModuleType("config")
    config_mod.PATCH_STREAM              = PATCH_STREAM
    config_mod.PATCH_SIZE                = PATCH_SIZE
    config_mod.PATCH_LENGTH              = cfg["PATCH_LENGTH"]
    config_mod.PATCH_NUM_LAYERS          = cfg["PATCH_NUM_LAYERS"]
    config_mod.CHAR_NUM_LAYERS           = cfg["CHAR_NUM_LAYERS"]
    config_mod.HIDDEN_SIZE               = cfg["HIDDEN_SIZE"]
    config_mod.PATCH_SAMPLING_BATCH_SIZE = 0
    config_mod.TOP_K                     = 9
    config_mod.TOP_P                     = 0.9
    config_mod.TEMPERATURE               = 1.2
    config_mod.INFERENCE_WEIGHTS_PATH    = ""
    config_mod.NUM_SAMPLES               = 1
    config_mod.ORIGINAL_OUTPUT_FOLDER    = "/tmp/notagen_orig"
    config_mod.INTERLEAVED_OUTPUT_FOLDER = "/tmp/notagen_interleaved"

    sys.modules["config"] = config_mod
    return cfg, original_config


def load_model(model_path: Optional[str] = None, size: str = "small"):
    """
    Load the NotaGen model from a .pth weights file.

    Args:
        model_path: Path to the weights .pth file or directory containing it.
                    If a directory, the first matching .pth file is used.
        size:       "small", "medium", or "large"

    Returns:
        (model, patchilizer, cfg)
    """
    cfg, original_config = _inject_config(size)

    try:
        # Import NotaGen classes while the fake config is active
        from utils import Patchilizer, NotaGenLMHeadModel
        from transformers import GPT2Config
    finally:
        # Always restore the original project config (even on import error)
        if original_config is not None:
            sys.modules["config"] = original_config
        elif "config" in sys.modules:
            del sys.modules["config"]

    # Locate weights file
    if model_path is None:
        default_dir = Path("models/NotaGen-small")
        candidates = list(default_dir.glob("*.pth"))
        if not candidates:
            raise FileNotFoundError(
                f"No .pth weights found in {default_dir}. "
                "Run the model download first."
            )
        weights_path = candidates[0]
    elif Path(model_path).is_dir():
        candidates = list(Path(model_path).glob("*.pth"))
        if not candidates:
            raise FileNotFoundError(f"No .pth file found in {model_path}")
        weights_path = candidates[0]
    else:
        weights_path = Path(model_path)

    print(f"  [NotaGen] Loading {size} model from: {weights_path}", flush=True)

    patch_config = GPT2Config(
        num_hidden_layers=cfg["PATCH_NUM_LAYERS"],
        max_length=cfg["PATCH_LENGTH"],
        max_position_embeddings=cfg["PATCH_LENGTH"],
        n_embd=cfg["HIDDEN_SIZE"],
        num_attention_heads=cfg["HIDDEN_SIZE"] // 64,
        vocab_size=1,
    )
    byte_config = GPT2Config(
        num_hidden_layers=cfg["CHAR_NUM_LAYERS"],
        max_length=PATCH_SIZE + 1,
        max_position_embeddings=PATCH_SIZE + 1,
        hidden_size=cfg["HIDDEN_SIZE"],
        num_attention_heads=cfg["HIDDEN_SIZE"] // 64,
        vocab_size=128,
    )

    model = NotaGenLMHeadModel(encoder_config=patch_config, decoder_config=byte_config)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  [NotaGen] Model parameters: {n_params:,}", flush=True)

    checkpoint = torch.load(str(weights_path), map_location="cpu")
    model.load_state_dict(checkpoint["model"])
    model.eval()

    patchilizer = Patchilizer()

    print(f"  [NotaGen] Model loaded on CPU.", flush=True)
    return model, patchilizer, cfg


# ── ABC generation ───────────────────────────────────────────────────────────

def _build_prompt_lines(notagen_prompt: str) -> list:
    """
    Convert a "Period|Composer|Instrumentation" string into the ABC metadata
    lines that NotaGen was fine-tuned on.
    """
    parts = notagen_prompt.split("|")
    period = parts[0].strip() if len(parts) > 0 else "Romantic"
    composer = parts[1].strip() if len(parts) > 1 else "Bach"
    instr = parts[2].strip() if len(parts) > 2 else "Chamber"

    # NotaGen fine-tune metadata format (from the README / training data)
    lines = [
        f"X:1\n",
        f"T:{period} - {instr}\n",
        f"C:{composer}\n",
        f"L:1/8\n",
        f"M:4/4\n",
        f"K:C\n",
    ]
    return lines


def generate_abc(
    model,
    patchilizer,
    cfg: dict,
    notagen_prompt: str,
    top_k: int = 9,
    top_p: float = 0.9,
    temperature: float = 1.2,
    timeout_seconds: int = 300,
    num_attempts: int = 2,
) -> Optional[str]:
    """
    Generate ABC notation using the NotaGen patch-based inference loop.

    Returns ABC text string or None on failure.
    """
    patch_length = cfg["PATCH_LENGTH"]
    prompt_lines = _build_prompt_lines(notagen_prompt)

    for attempt in range(1, num_attempts + 1):
        print(f"  [NotaGen] ABC generation attempt {attempt}/{num_attempts} "
              f"| '{notagen_prompt}'", flush=True)
        t0 = time.time()

        # Encode prompt metadata into patches
        prompt_patches = patchilizer.patchilize_metadata(prompt_lines)
        byte_list = list("".join(prompt_lines))

        bos_patch = [patchilizer.bos_token_id] * (PATCH_SIZE - 1) + [patchilizer.eos_token_id]
        prompt_patches = [
            [ord(c) for c in patch] + [patchilizer.special_token_id] * (PATCH_SIZE - len(patch))
            for patch in prompt_patches
        ]
        prompt_patches.insert(0, bos_patch)

        input_patches = torch.tensor(prompt_patches).reshape(1, -1)

        failure_flag = False
        end_flag = False
        cut_index = None
        tunebody_flag = False

        try:
            with torch.no_grad():
                while True:
                    predicted_patch = model.generate(
                        input_patches.unsqueeze(0),
                        top_k=top_k,
                        top_p=top_p,
                        temperature=temperature,
                    )

                    # Inject [r:0/ prefix for first tunebody line
                    if (not tunebody_flag and
                            patchilizer.decode([predicted_patch]).startswith("[r:")):
                        tunebody_flag = True
                        r0 = torch.tensor([ord(c) for c in "[r:0/"]).unsqueeze(0)
                        temp_input = torch.cat([input_patches, r0], dim=-1)
                        predicted_patch = model.generate(
                            temp_input.unsqueeze(0),
                            top_k=top_k, top_p=top_p, temperature=temperature,
                        )
                        predicted_patch = [ord(c) for c in "[r:0/"] + predicted_patch

                    # EOS check
                    if (predicted_patch[0] == patchilizer.bos_token_id and
                            predicted_patch[1] == patchilizer.eos_token_id):
                        end_flag = True
                        break

                    next_patch = patchilizer.decode([predicted_patch])
                    for char in next_patch:
                        byte_list.append(char)

                    # Pad short patches
                    for j in range(len(predicted_patch)):
                        if predicted_patch[j] == patchilizer.eos_token_id:
                            for k in range(j + 1, len(predicted_patch)):
                                predicted_patch[k] = patchilizer.special_token_id
                            break

                    predicted_patch_t = torch.tensor([predicted_patch])
                    input_patches = torch.cat([input_patches, predicted_patch_t], dim=1)

                    # Safety limits
                    if len(byte_list) > 102400:
                        failure_flag = True
                        break
                    if time.time() - t0 > timeout_seconds:
                        print(f"  [NotaGen] Timeout after {timeout_seconds}s", flush=True)
                        failure_flag = True
                        break

                    # Stream sliding window when context is full
                    if (input_patches.shape[1] >= patch_length * PATCH_SIZE and not end_flag):
                        abc_code = "".join(byte_list)
                        abc_lines_raw = abc_code.split("\n")

                        tunebody_index = None
                        for i, line in enumerate(abc_lines_raw):
                            if line.startswith("[r:") or line.startswith("[V:"):
                                tunebody_index = i
                                break

                        if tunebody_index is None or tunebody_index == len(abc_lines_raw) - 1:
                            break

                        metadata_lines_raw = abc_lines_raw[:tunebody_index]
                        tunebody_lines_raw = abc_lines_raw[tunebody_index:]

                        metadata_lines_raw = [l + "\n" for l in metadata_lines_raw]
                        if not abc_code.endswith("\n"):
                            tunebody_lines_raw = (
                                [l + "\n" for l in tunebody_lines_raw[:-1]] + [tunebody_lines_raw[-1]]
                            )
                        else:
                            tunebody_lines_raw = [l + "\n" for l in tunebody_lines_raw]

                        if cut_index is None:
                            cut_index = len(tunebody_lines_raw) // 2

                        abc_slice = "".join(metadata_lines_raw + tunebody_lines_raw[-cut_index:])
                        new_patches = patchilizer.encode_generate(abc_slice)
                        new_patches = [item for sub in new_patches for item in sub]
                        input_patches = torch.tensor([new_patches]).reshape(1, -1)

        except Exception as e:
            print(f"  [NotaGen] Generation error: {e}", flush=True)
            import traceback; traceback.print_exc()
            failure_flag = True

        elapsed = time.time() - t0
        abc_text = "".join(byte_list)

        if not failure_flag and abc_text.strip():
            print(f"  [NotaGen] Generated {len(abc_text)} chars in {elapsed:.1f}s", flush=True)
            return abc_text
        else:
            print(f"  [NotaGen] Attempt {attempt} failed (failure={failure_flag}, "
                  f"chars={len(abc_text)}). Retrying...", flush=True)

    return None


# ── High-level section generator ─────────────────────────────────────────────

def generate_section(
    model,
    tokenizer,          # This is actually (patchilizer, cfg) — see midi_llm_api.py
    style_desc: str,
    instrument_name: str,
    bpm: float,
    section_name: str,
    bars: int,
    polyphony_limit: int,
    grid: str,
    density: float,
    pitch_range: Optional[List[int]],
    transition: str,
    is_drum: bool,
    output_path: Path,
    instrument_program: int = 0,
    velocity_base: int = 80,
) -> Optional[Path]:
    """
    Generate a single section track.

    NOTE: `tokenizer` here is (patchilizer, cfg) tuple to match
    the FastAPI lifespan which returns (model, tokenizer) where tokenizer
    is repurposed to carry these two objects.

    Drum tracks → deterministic rule-based generator.
    Melodic tracks → NotaGen ABC generation → abc_to_midi converter.
    """
    from notagen import drum_generator, abc_to_midi as abc_converter

    patchilizer, cfg = tokenizer  # unpack from the repurposed slot

    # ── Drum tracks bypass NotaGen ──────────────────────────────────────────
    if is_drum:
        print(f"  [NotaGen] Drum '{instrument_name}' → rule-based generator", flush=True)
        try:
            drum_generator.generate(
                style_desc=style_desc,
                density=density,
                grid=grid,
                bars=bars,
                bpm=bpm,
                polyphony_limit=polyphony_limit,
                transition=transition,
                pitch_range=pitch_range,
                output_path=output_path,
                velocity_base=velocity_base,
            )
            return output_path
        except Exception as e:
            print(f"  [NotaGen] Drum error: {e}", flush=True)
            return None

    # ── Melodic tracks: NotaGen → ABC → MIDI ────────────────────────────────
    notagen_prompt = build_notagen_prompt(style_desc, instrument_name, bpm, section_name)

    abc_str = generate_abc(
        model=model,
        patchilizer=patchilizer,
        cfg=cfg,
        notagen_prompt=notagen_prompt,
        top_k=9,
        top_p=0.9,
        temperature=1.2,
        timeout_seconds=300,
        num_attempts=2,
    )

    if not abc_str:
        print(f"  [NotaGen] No ABC output for '{instrument_name}'", flush=True)
        return None

    try:
        result = abc_converter.abc_to_midi(
            abc_str=abc_str,
            output_path=output_path,
            bpm=bpm,
            bars=bars,
            polyphony_limit=polyphony_limit,
            grid=grid,
            pitch_range=pitch_range,
            instrument_program=instrument_program,
            is_drum=False,
            transition=transition,
            instrument_name=instrument_name,
            velocity_base=velocity_base,
        )
        if result:
            actual_poly = abc_converter.count_max_simultaneous(Path(output_path))
            icon = "✓" if actual_poly <= polyphony_limit else "✗ VIOLATION"
            print(f"  [NotaGen] {icon} '{instrument_name}': poly {actual_poly}/{polyphony_limit}",
                  flush=True)
        return result
    except Exception as e:
        print(f"  [NotaGen] ABC→MIDI error for '{instrument_name}': {e}", flush=True)
        import traceback; traceback.print_exc()
        return None
