import random
from core.structures import STRUCTURE_TEMPLATES
from core.style_config import STYLE_DATA
from llm.ollama_client import ask_llm

def expand_prompt(genre, topic):
    """
    Uses a standard LLM (Ollama) to expand a simple genre/topic into a 
    rich musical description following researched style data.
    """
    templates = STRUCTURE_TEMPLATES.get(genre, [])
    template = random.choice(templates) if templates else {"name": "Standard", "description": "Generic structure", "sections": ["Intro", "Verse", "Chorus", "Outro"]}
    
    style = STYLE_DATA.get(genre, {})
    
    production_options = f"""
- BPM RANGES: {style.get('bpm_ranges', '100-120')}
- HARMONY OPTIONS: {', '.join(style.get('harmonies', []))}
- INSTRUMENT POOL: {', '.join(style.get('common_instruments', []))}
- EFFECTS: {', '.join(style.get('effects', []))}
- STRUCTURE OPTIONS: {style.get('structures', ['Standard'])[0]}
- PIANO SOLO STYLE: {style.get('piano_solo_style', 'Standard')}
"""

    template_str = f"Template: {template['name']}\nDescription: {template['description']}\nSections: {', '.join(template['sections'])}"

    prompt = f"""
You are a professional music producer and director. 
Expand the following musical idea into a highly detailed production plan.
GENRE: {genre}
TOPIC: {topic}

PRODUCTION OPTIONS (Select the best for this topic):
{production_options}

STRUCTURE TEMPLATE TO FOLLOW:
{template_str}

 Your expansion MUST:
1. Select a specific BPM and Harmony from the options above.
2. Elaborate on the mood, atmosphere, and 'personality' of the song.
3. Define a rich, multitrack instrumentation (at least 10-14 tracks) using the pool above.
4. MOTIVIC DEVELOPMENT: Describe a central 'hook' or 'motif' (a short 4-8 note idea) that repeats and evolves throughout the song.
5. Describe specific transitions, 'drops', and 'fills' between the sections.
6. Ensure the personality reflects the '{genre}' style deeply.

Output the expansion as a single, coherent, highly descriptive paragraph.
"""

    return ask_llm(prompt)
