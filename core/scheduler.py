def create_schedule(plan):

    current_bar = 0

    schedule = []

    for section in plan["sections"]:

        schedule.append({

            "name": section["name"],

            "start_bar": current_bar,

            "end_bar": (
                current_bar +
                section["bars"]
            ),

            "energy": section["energy"]

        })

        current_bar += section["bars"]

    return schedule
