from fractions import Fraction as F

import pytest

from complib import (DOUBLE_DOT, DOT, EIGHTH, QUARTER, SIXTEENTH, THIRTY_SECOND,
                     WHOLE, HALF, Chord, Event, Note, Part, Pitch, Rest, Score,
                     SyntaxError, _duration_type)


def test_duration_constants():
    assert WHOLE == F(1)
    assert HALF == F(1, 2)
    assert QUARTER == F(1, 4)
    assert EIGHTH == F(1, 8)
    assert SIXTEENTH == F(1, 16)
    assert THIRTY_SECOND == F(1, 32)
    assert DOT == F(3, 2)
    assert DOUBLE_DOT == F(7, 4)


def test_note_converts_string_pitch():
    note = Note('c')
    assert note.pitches == [Pitch('c')]
    assert note.duration == QUARTER


def test_event_rejects_illegal_pitch():
    with pytest.raises(SyntaxError):
        Note(0)
    with pytest.raises(SyntaxError):
        Event([None])


@pytest.mark.parametrize('left,right,equal', [
    (Note('c'), Note('c'), True),
    (Note('c', F(1, 2)), Note('c', F(1, 2)), True),
    (Note('c'), Note('c', F(1, 2)), False),
    (Note('c'), Note('d'), False),
    (Note('c'), Chord(['c']), False),
    (Note('c'), Rest(), False),
    (Rest(), Rest(F(1, 2)), False),
])
def test_event_equality(left, right, equal):
    assert (left == right) is equal
    assert (right == left) is equal


def test_event_hash_matches_equality():
    assert hash(Note('c')) == hash(Note('c'))
    assert len({Note('c'), Note('c', F(1, 2))}) == 2
    assert len({Note('c'), Chord(['c']), Rest()}) == 3


def test_event_not_equal_to_other_types():
    assert Note('c') != 'c'
    assert Note('c') != ()


def test_event_str_repr():
    assert str(Note('c4')) == 'c4 1/4'
    assert str(Rest(F(1, 2))) == 'r 1/2'
    assert str(Rest()) == 'r 1/4'
    assert str(Chord(['c', 'e'])) == 'c4 e4 1/4'
    assert repr(Note('c')) == "Note('c', 1/4)"
    assert repr(Rest()) == "Rest(1/4)"
    assert repr(Chord(['c', 'e'])) == "Chord('c4 e4', 1/4)"


def test_event_midipitches():
    assert Chord(['c', 'e']).midipitches() == [60, 64]
    assert Rest().midipitches() == []


def test_chord_voices_low_to_high():
    chord = Chord(['c', 'e', 'g'])
    assert [str(p) for p in chord.pitches] == ['c4', 'e4', 'g4']
    assert str(Chord(['c', 'e', 'g', 'c', 'c'])) == 'c4 e4 g4 c5 c6 1/4'


def test_chord_respects_explicit_octaves():
    assert [str(p) for p in Chord(['c3', 'e4']).pitches] == ['c3', 'e4']
    assert [str(p) for p in Chord(['g2', 'c']).pitches] == ['g2', 'c3']


def test_chord_rejects_past_octave_range():
    with pytest.raises(SyntaxError):
        Chord(['c7', 'c'])


@pytest.mark.parametrize('duration,expected', [
    (F(1), ('whole', 0, None, None)),
    (F(1, 2), ('half', 0, None, None)),
    (F(1, 4), ('quarter', 0, None, None)),
    (F(1, 8), ('eighth', 0, None, None)),
    (F(1, 16), ('16th', 0, None, None)),
    (F(1, 32), ('32nd', 0, None, None)),
    (F(1, 64), ('64th', 0, None, None)),
    (F(1, 128), ('128th', 0, None, None)),
    (F(3, 2), ('whole', 1, None, None)),
    (F(3, 4), ('half', 1, None, None)),
    (F(3, 8), ('quarter', 1, None, None)),
    (F(3, 16), ('eighth', 1, None, None)),
    (F(7, 16), ('quarter', 2, None, None)),
    (F(7, 32), ('eighth', 2, None, None)),
    (F(1, 12), ('eighth', 0, 3, 2)),
    (F(1, 3), ('half', 0, 3, 2)),
    (F(1, 5), ('quarter', 0, 5, 4)),
    (F(1, 96), ('64th', 0, 3, 2)),
    (0, ('quarter', 0, None, None)),
])
def test_duration_type(duration, expected):
    assert _duration_type(duration) == expected


def test_part_defaults():
    part = Part([Note('c')])
    assert part.name == 'Music'
    assert str(part) == 'Music'
    assert repr(part) == "Part('Music', 1 events)"


def test_part_named():
    part = Part([Note('c'), Note('d')], 'Flute')
    assert part.name == 'Flute'
    assert part.sequence == [Note('c'), Note('d')]
    assert str(part) == 'Flute'
    assert repr(part) == "Part('Flute', 2 events)"


def test_part_rejects_empty():
    with pytest.raises(SyntaxError):
        Part([])


def test_part_rejects_non_event():
    with pytest.raises(SyntaxError):
        Part(['c'])


def test_score_defaults():
    score = Score([Part([Note('c')])])
    assert score.time == '4/4'
    assert score.beats == 4
    assert score.beat_type == 4


@pytest.mark.parametrize('time,beats,beat_type', [
    ('1/4', 1, 4),
    ('2/2', 2, 2),
    ('3/8', 3, 8),
    ('4/4', 4, 4),
    ('5/4', 5, 4),
    ('6/8', 6, 8),
    ('7/8', 7, 8),
    ('12/16', 12, 16),
])
def test_score_parses_time(time, beats, beat_type):
    score = Score([Part([Note('c')])], time)
    assert score.beats == beats
    assert score.beat_type == beat_type


@pytest.mark.parametrize('bad', ['', '4', '/4', '4/', 'x/4', '4/x', '0/4', '4/3',
                                '4/5', '4/4+2/8', '4/4 ', ' 4/4', '-4/4'])
def test_score_rejects_time(bad):
    with pytest.raises(SyntaxError):
        Score([Part([Note('c')])], bad)


def test_score_rejects_empty():
    with pytest.raises(SyntaxError):
        Score([])


def test_score_rejects_non_part():
    with pytest.raises(SyntaxError):
        Score([Note('c')])


def test_score_str_repr():
    score = Score([Part([Note('c')], 'Flute'), Part([Note('d')], 'Oboe')], '6/8')
    assert str(score) == 'Flute, Oboe in 6/8'
    assert repr(score) == ("Score(Part('Flute', 1 events), "
                           "Part('Oboe', 1 events), '6/8')")
