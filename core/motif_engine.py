import random


def mutate_motif(motif):

    idx = random.randint(
        0,
        len(motif)-1
    )

    note, start, duration, velocity = motif[idx]

    velocity += random.randint(-5, 5)

    motif[idx] = (
        note,
        start,
        duration,
        velocity
    )

    return motif
