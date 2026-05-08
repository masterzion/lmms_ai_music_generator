import random


def apply_chillout(events):

    output = []

    for e in events:

        note, start, duration, velocity = e

        start += random.uniform(
            -0.05,
            0.05
        )

        velocity -= 10

        output.append(
            (
                note,
                start,
                duration,
                velocity
            )
        )

    return output
