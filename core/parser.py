import re


def parse_prompt(user_prompt):
    from core.style_config import STYLE_DATA
    pattern = r"<(.*?)>"
    match = re.search(pattern, user_prompt)
    if not match:
        raise Exception("Missing genre tag")
    genre = match.group(1).lower()
    if genre not in STYLE_DATA.keys():
        raise Exception(f"Invalid genre. Supported: {list(STYLE_DATA.keys())}")

    topic = re.sub(pattern, "", user_prompt).strip()

    return genre, topic
