from fractions import Fraction as F

import pytest

from complib import (DOUBLE_DOT, DOT, EIGHTH, QUARTER, SIXTEENTH, THIRTY_SECOND,
                     WHOLE, HALF, Idea, Part, Score, SyntaxError, _duration_type,
                     degrees, pitches, rhythm)


def test_duration_constants():
    assert WHOLE == F(1)
    assert HALF == F(1, 2)
    assert QUARTER == F(1, 4)
    assert EIGHTH == F(1, 8)
    assert SIXTEENTH == F(1, 16)
    assert THIRTY_SECOND == F(1, 32)
    assert DOT == F(3, 2)
    assert DOUBLE_DOT == F(7, 4)


def test_empty_idea_is_valid():
    idea = Idea()
    assert idea.pitches is None
    assert idea.degrees is None
    assert idea.rhythm is None


def test_idea_rejects_pitches_and_degrees():
    with pytest.raises(SyntaxError):
        Idea(pitches=[], degrees=[])


def test_idea_fields():
    idea = Idea(pitches=[['c']], rhythm=[F(1, 4)])
    assert idea.pitches == [['c']]
    assert idea.degrees is None
    assert idea.rhythm == [F(1, 4)]


def test_idea_repr():
    assert repr(Idea()) == 'Idea()'
    assert repr(pitches('c')) == "Idea(pitches=[[Pitch('c0')]])"
    assert repr(rhythm('/4')) == 'Idea(rhythm=[Fraction(1, 4)])'


def test_chord_voices_low_to_high():
    assert [str(p) for p in pitches('<c e g>').pitches[0]] == ['c0', 'e0', 'g0']
    assert [str(p) for p in pitches('<c e g c c>').pitches[0]] == ['c0', 'e0', 'g0', 'c1', 'c2']


def test_chord_respects_explicit_octaves():
    assert [str(p) for p in pitches('<c3 e4>').pitches[0]] == ['c3', 'e4']
    assert [str(p) for p in pitches('<g2 c>').pitches[0]] == ['g2', 'c3']


def test_chord_stacks_past_octave_range():
    assert [str(p) for p in pitches('<c7 c>').pitches[0]] == ['c7', 'c8']


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
    part = Part(pitches('c') + rhythm('/4'))
    assert part.name == 'Music'
    assert str(part) == 'Music'
    assert repr(part) == "Part('Music', 1 events)"


def test_part_named():
    part = Part(pitches('c d') + rhythm('/4'), 'Flute')
    assert part.name == 'Flute'
    assert str(part) == 'Flute'
    assert repr(part) == "Part('Flute', 2 events)"

def test_part_rejects_degrees():
    with pytest.raises(SyntaxError):
        Part(degrees('1'))


def test_score_defaults():
    score = Score([Part(pitches('c') + rhythm('/4'))])
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
    score = Score([Part(pitches('c') + rhythm('/4'))], time)
    assert score.beats == beats
    assert score.beat_type == beat_type


@pytest.mark.parametrize('bad', ['', '4', '/4', '4/', 'x/4', '4/x', '0/4', '4/3',
                                '4/5', '4/4+2/8', '4/4 ', ' 4/4', '-4/4'])
def test_score_rejects_time(bad):
    with pytest.raises(SyntaxError):
        Score([Part(pitches('c') + rhythm('/4'))], bad)


def test_score_rejects_empty():
    with pytest.raises(SyntaxError):
        Score([])


def test_score_rejects_non_part():
    with pytest.raises(SyntaxError):
        Score([Idea()])


def test_score_str_repr():
    score = Score([Part(pitches('c') + rhythm('/4'), 'Flute'),
                   Part(pitches('d') + rhythm('/4'), 'Oboe')], '6/8')
    assert str(score) == 'Flute, Oboe in 6/8'
    assert repr(score) == ("Score(Part('Flute', 1 events), "
                           "Part('Oboe', 1 events), '6/8')")
