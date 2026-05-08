import pretty_midi


def render_song(song):

    song.write(
        "outputs/song.mid"
    )
