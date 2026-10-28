import pytest

from musicat import Part, Score, deg, rhy


@pytest.fixture
def built(monkeypatch):
    """Spy on the PrettyMIDI object play() builds; silence the Audio display."""
    pretty_midi = pytest.importorskip('pretty_midi')
    ipython = pytest.importorskip('IPython.display')
    captured = {}
    real = pretty_midi.PrettyMIDI

    def spy(*args, **kwargs):
        midi = real(*args, **kwargs)
        captured['midi'] = midi
        return midi

    monkeypatch.setattr(pretty_midi, 'PrettyMIDI', spy)
    monkeypatch.setattr(ipython, 'display', lambda *args: None)
    return captured


def pitches(instrument):
    return [note.pitch for note in instrument.notes]


def test_play_builds_notes_at_middle_c(built):
    idea = deg('1 2 3') @ rhy('4 4 4')
    idea.play()
    midi = built['midi']
    assert pitches(midi.instruments[0]) == [60, 62, 64]
    notes = midi.instruments[0].notes
    assert [(n.start, n.end) for n in notes] == [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5)]


def test_play_keeps_chords_and_rests(built):
    idea = deg('1 <3 5> 7') @ rhy('4 r4 4')
    Score([Part(idea, 'X')]).play()
    notes = built['midi'].instruments[0].notes
    assert [(n.start, n.pitch) for n in notes] == [(0.0, 60), (1.0, 64), (1.0, 67), (1.5, 71)]


def test_play_gives_each_part_its_own_instrument(built):
    melody = deg('1 2 3') @ rhy('4 4 4')
    bass = deg('1 1 1') @ rhy('4 4 4')
    Score([Part(melody, 'Melody'), Part(bass, 'Bass')]).play()
    instruments = built['midi'].instruments
    assert len(instruments) == 2
    assert pitches(instruments[0]) == [60, 62, 64]
    assert pitches(instruments[1]) == [60, 60, 60]
