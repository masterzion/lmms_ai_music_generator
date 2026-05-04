from typing import List, Dict, Union, Optional, Any
from pydantic import BaseModel, Field, field_validator

class Meta(BaseModel):
    bpm: int = Field(..., ge=40, le=240)
    scale: str = Field(default="minor")
    intervals: Optional[List[int]] = None 
    root_midi: int = Field(default=48, ge=0, le=127) # New: Direct MIDI root
    genre: str = "EBM"
    title: str = "Untitled" # New: Song Title
    folder: str = "misc"    # New: Thematic Folder (e.g., ebm/war)
    swing: float = Field(default=0.0, ge=0.0, le=1.0)

class Section(BaseModel):
    section: str
    bars: int = Field(..., gt=0)

class Track(BaseModel):
    type: str  # "drum_machine", "monophonic", or "poly"
    root: Optional[str] = "A2"
    patterns: Optional[Dict[str, Any]] = None # Ultimate flexibility
    motifs: Optional[Dict[str, Any]] = None   # Ultimate flexibility
    schedule: Optional[List[int]] = None 
    density: Optional[float] = 0.6
    octave: Optional[int] = 4

class Variation(BaseModel):
    probability: float = Field(default=0.1, ge=0.0, le=1.0)
    operations: List[str] = Field(default_factory=list)

class Composition(BaseModel):
    meta: Meta
    structure: List[Section]
    tracks: Dict[str, Track]
    variation: Optional[Variation] = None
