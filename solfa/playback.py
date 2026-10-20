from .degrees import white_keys
from .score import Score


def play(score: Score):
    import pretty_midi
    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    for part in score.parts:
        instrument = pretty_midi.Instrument(program=0)
        offset = 0.0
        for group, duration in part.idea.events():
            end = offset + float(duration) * 2
            for number, alter in group:
                pitch = white_keys._at((number, 0))[0] + (alter or 0) + 60
                instrument.notes.append(pretty_midi.Note(
                    velocity=80, pitch=pitch, start=offset, end=end))
            offset = end
        midi.instruments.append(instrument)
    try:
        from IPython.display import Audio, display
        display(Audio(midi.synthesize(), rate=44100))
    except ImportError:
        pass
