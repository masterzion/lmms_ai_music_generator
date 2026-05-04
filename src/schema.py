from typing import List, Dict, Union, Optional
from pydantic import BaseModel, Field, field_validator

class Meta(BaseModel):
    bpm: int = Field(..., ge=40, le=240)
    scale: str = Field(default="A_minor")
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
    patterns: Optional[Dict[str, Union[Dict[str, str], List[Union[int, str, List[int]]]]]] = None
    motifs: Optional[Dict[str, List[Union[int, str]]]] = None # For poly
    schedule: Optional[List[int]] = None # New: List of section indices where track is active
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
