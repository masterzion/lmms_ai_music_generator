from typing import List, Dict, Union, Optional
from pydantic import BaseModel, Field, field_validator

class Meta(BaseModel):
    bpm: int = Field(..., ge=40, le=240)
    scale: str = Field(default="A_minor")  # Format: [Root]_[ScaleType] (e.g., A_minor, C_phrygian)
    swing: float = Field(default=0.0, ge=0.0, le=1.0)
    style: Optional[Dict[str, Union[str, float]]] = None

class Section(BaseModel):
    section: str
    bars: int = Field(..., gt=0)

class Track(BaseModel):
    type: str  # "drum_machine", "monophonic", or "poly"
    root: Optional[str] = "A2"
    # For drums: dict of 16-char strings. For melody: dict of lists of 16 ints.
    patterns: Optional[Dict[str, Union[Dict[str, str], List[int]]]] = None
    motifs: Optional[Dict[str, List[int]]] = None # For poly
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
