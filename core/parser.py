import re


VALID_TAGS = [
    "ebm",
    "futurepop",
    "chillout"
]


def parse_prompt(user_prompt):

    pattern = r"<(.*?)>"

    match = re.search(pattern, user_prompt)

    if not match:
        raise Exception("Missing genre tag")

    genre = match.group(1)

    if genre not in VALID_TAGS:
        raise Exception("Invalid genre")

    topic = re.sub(pattern, "", user_prompt).strip()

    return genre, topic
