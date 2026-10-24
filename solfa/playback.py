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
        import numpy as np
        try:
            audio = midi.synthesize(fs=44100)
        except Exception:
            audio = None
        if audio is not None:
            audio = np.array(audio)
            if audio.size == 0 or not np.isfinite(audio).all():
                audio = np.zeros(int(44100 * 0.01), dtype=float)
            elif np.max(np.abs(audio)) == 0:
                audio = np.zeros(int(44100 * 0.01), dtype=float)
            else:
                audio = audio / np.max(np.abs(audio))
            display(Audio(audio, rate=44100))
        else:
            display(Audio(np.zeros(int(44100 * 0.01)), rate=44100))
    except ImportError:
        pass
