def apply_ebm(events):

    output = []

    for e in events:

        note, start, duration, velocity = e

        start = round(start * 4) / 4

        velocity = min(127, velocity + 10)

        output.append(
            (
                note,
                start,
                duration,
                velocity
            )
        )

    return output
