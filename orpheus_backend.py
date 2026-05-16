import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from pathlib import Path
from typing import List, Optional
import mido

# ── Orpheus-1 Architecture (Refined) ──────────────────────────────────────────

class RotaryEmbedding(nn.Module):
    def __init__(self, dim):
        super().__init__()
        inv_freq = 1.0 / (10000 ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq)

    def forward(self, max_seq_len, device):
        t = torch.arange(max_seq_len, device=device).type_as(self.inv_freq)
        freqs = torch.einsum("i,j->ij", t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        return emb

def rotate_half(x):
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)

def apply_rotary_pos_emb(q, k, freqs):
    # Ensure freqs matches q,k dimensions
    freqs = freqs[:q.shape[-2], :].unsqueeze(0).unsqueeze(1)
    return (q * freqs.cos()) + (rotate_half(q) * freqs.sin()), \
           (k * freqs.cos()) + (rotate_half(k) * freqs.sin())

class OrpheusAttention(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.heads = heads
        self.scale = (dim // heads) ** -0.5
        self.to_qkv = nn.Linear(dim, dim * 3, bias=False)
        self.to_out = nn.Linear(dim, dim)

    def forward(self, x, freqs=None, mask=None):
        h = self.heads
        q, k, v = self.to_qkv(x).chunk(3, dim=-1)
        q, k, v = map(lambda t: t.view(*t.shape[:-1], h, -1).transpose(1, 2), (q, k, v))

        if freqs is not None:
            q, k = apply_rotary_pos_emb(q, k, freqs)

        dots = torch.einsum("bhid,bhjd->bhij", q, k) * self.scale
        if mask is not None:
            dots.masked_fill_(mask, float("-inf"))

        attn = dots.softmax(dim=-1)
        out = torch.einsum("bhij,bhjd->bhid", attn, v)
        out = out.transpose(1, 2).reshape(*x.shape)
        return self.to_out(out)

class OrpheusBlock(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.attn = OrpheusAttention(dim, heads)
        self.ff = nn.Sequential(
            nn.Linear(dim, dim * 4),
            nn.GELU(),
            nn.Linear(dim * 4, dim)
        )
        self.norm1 = nn.LayerNorm(dim)
        self.norm2 = nn.LayerNorm(dim)

    def forward(self, x, freqs=None, mask=None):
        x = x + self.attn(self.norm1(x), freqs, mask)
        x = x + self.ff(self.norm2(x))
        return x

class OrpheusTransformer(nn.Module):
    def __init__(self, vocab_size=32768, dim=1536, depth=24, heads=16):
        super().__init__()
        self.token_emb = nn.Embedding(vocab_size, dim)
        self.rotary_emb = RotaryEmbedding(dim // heads)
        self.layers = nn.ModuleList([OrpheusBlock(dim, heads) for _ in range(depth)])
        self.to_logits = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, vocab_size, bias=False)
        )

    def forward(self, x):
        device = x.device
        seq_len = x.shape[1]
        freqs = self.rotary_emb(seq_len, device)
        mask = torch.triu(torch.ones(seq_len, seq_len, device=device), diagonal=1).bool()
        x = self.token_emb(x)
        for layer in self.layers:
            x = layer(x, freqs=freqs, mask=mask)
        return self.to_logits(x)

# ── Orpheus Backend ───────────────────────────────────────────────────────────

class OrpheusBackend:
    def __init__(self, model_path: str, use_fp16: bool = False):
        print(f"  [Orpheus] Initializing from {model_path} (FP16: {use_fp16})...", flush=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if use_fp16 else torch.float32
        self.model = OrpheusTransformer().to(self.device).to(self.dtype)
        
        try:
            state_dict = torch.load(model_path, map_location=self.device)
            if "model" in state_dict: state_dict = state_dict["model"]
            
            # Print state dict keys for debugging
            first_key = list(state_dict.keys())[0]
            print(f"  [Orpheus] Found weights with shape: {state_dict[first_key].shape}", flush=True)
            
            msg = self.model.load_state_dict(state_dict, strict=False)
            print(f"  [Orpheus] Load report: {msg}", flush=True)
        except Exception as e:
            print(f"  [Orpheus] CRITICAL LOAD ERROR: {e}", flush=True)
            
        self.model.eval()

    def generate(self, prompt_tokens: List[int], max_len=256, temperature=0.9):
        x = torch.tensor([prompt_tokens], device=self.device)
        for _ in range(max_len):
            with torch.no_grad():
                logits = self.model(x[:, -2048:])
                logits = logits[:, -1, :] / temperature
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                x = torch.cat((x, next_token), dim=1)
                if next_token.item() == 0: break
        
        generated = x[0].tolist()
        print(f"  [Orpheus] Generated {len(generated)} tokens. Sample: {generated[:10]}...", flush=True)
        return generated

def decode_orpheus_tokens(tokens: List[int]) -> mido.MidiFile:
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Orpheus Standard Resolution
    current_time = 0
    
    # Orpheus tokens are often: [Wait, Pitch, Duration, Velocity] or [Wait, Pitch, Vel+Dur]
    # Here we assume the most robust mapping for Orpheus-1
    for i in range(0, len(tokens) - 3, 4):
        wait = tokens[i]
        pitch = tokens[i+1]
        dur = tokens[i+2]
        vel = tokens[i+3]
        
        # Mapping tokens to MIDI values (Orpheus-1 scale)
        if 0 <= pitch <= 127:
            wait_ms = max(0, (wait - 256) * 10) if wait >= 256 else 0
            current_time += int(wait_ms)
            
            # Add Note
            track.append(mido.Message('note_on', note=pitch, velocity=min(127, vel), time=current_time))
            # Fixed duration if dur token is weird
            track.append(mido.Message('note_off', note=pitch, velocity=0, time=480))
            current_time = 0 # Reset for relative time
            
    return mid
