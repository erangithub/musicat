from fractions import Fraction as F

import pytest

from complib import (Chord, Note, Pitch, Rest, SyntaxError, combine, major_scale,
                     to_pitches, to_rhythm)


@pytest.mark.parametrize('name,root,accidental,octave', [
    ('c', 'c', None, None),
    ('C', 'C', None, None),
    ('f#4', 'f', '#', 4),
    ('bb3', 'b', 'b', 3),
    ('g##', 'g', '##', None),
    ('e-1', 'e', None, -1),
    ('a7', 'a', None, 7),
    ('d#', 'd', '#', None),
])
def test_pitch_parses(name, root, accidental, octave):
    pitch = Pitch(name)
    assert pitch.root == root
    assert pitch.accidental == accidental
    assert pitch.octave == octave


@pytest.mark.parametrize('bad', ['', 'h', 'cc', 'i4', 'c8', 'c#b4', 'c#-2', 'c bb'])
def test_pitch_rejects(bad):
    with pytest.raises(SyntaxError):
        Pitch(bad)


@pytest.mark.parametrize('name,midipitch', [
    ('c', 0),
    ('c-1', 0),
    ('e-1', 4),
    ('c4', 60),
    ('f#4', 66),
    ('bb3', 58),
    ('a4', 69),
    ('a7', 105),
])
def test_pitch_midipitch(name, midipitch):
    assert Pitch(name).midipitch() == midipitch


@pytest.mark.parametrize('a,b,equal', [
    ('c4', 'c4', True),
    ('C4', 'c4', True),
    ('c4', 'c', False),
    ('c#4', 'db4', False),
    ('c4', 'd4', False),
])
def test_pitch_equality(a, b, equal):
    assert (Pitch(a) == Pitch(b)) is equal


def test_pitch_hash():
    assert len({Pitch('c4'), Pitch('c4'), Pitch('d4')}) == 2


def test_pitch_not_equal_to_other_types():
    assert Pitch('c4') != 'c4'
    assert Pitch('c4') != None


def test_pitch_str_repr():
    pitch = Pitch('f#4')
    assert str(pitch) == 'f#4'
    assert repr(pitch) == "Pitch('f#4')"


@pytest.mark.parametrize('root,pitches', [
    ('c', ['c', 'd', 'e', 'f', 'g', 'a', 'b']),
    ('d', ['d', 'e', 'f#', 'g', 'a', 'b', 'c#']),
    ('g', ['g', 'a', 'b', 'c', 'd', 'e', 'f#']),
    ('bb', ['bb', 'c', 'd', 'eb', 'f', 'g', 'a']),
])
def test_major_scale(root, pitches):
    assert [str(p) for p in major_scale(root)] == pitches


def test_major_scale_rejects_illegal_root():
    with pytest.raises(SyntaxError):
        major_scale('h')


@pytest.mark.parametrize('text,groups', [
    ('', []),
    ('c', [['c']]),
    ('c d e', [['c'], ['d'], ['e']]),
    ('c4 d4', [['c4'], ['d4']]),
    ('c <e g>', [['c'], ['e', 'g']]),
    ('<d>', [['d']]),
    ('<>', [[]]),
    ('c <> <e g>', [['c'], [], ['e', 'g']]),
])
def test_to_pitches(text, groups):
    assert to_pitches(text) == [[Pitch(p) for p in group] for group in groups]


@pytest.mark.parametrize('bad', ['c <e g', 'c e>', '<<c>>', '<>x', 'h', 'c <c <e>>'])
def test_to_pitches_rejects(bad):
    with pytest.raises(SyntaxError):
        to_pitches(bad)


@pytest.mark.parametrize('text,durations', [
    ('', []),
    ('/4', [F(1, 4)]),
    ('1/4', [F(1, 4)]),
    ('1', [F(1)]),
    ('/2', [F(1, 2)]),
    ('1/2.', [F(3, 4)]),
    ('1/8.', [F(3, 16)]),
    ('1/8..', [F(7, 32)]),
    ('/16.', [F(3, 32)]),
    ('1/4 /8 /2', [F(1, 4), F(1, 8), F(1, 2)]),
])
def test_to_rhythm(text, durations):
    assert to_rhythm(text) == durations


@pytest.mark.parametrize('bad', ['.', '/.', '1/0', '/0', 'x', '4//2', '1/4x', '/',
                                '1/', '4.5'])
def test_to_rhythm_rejects(bad):
    with pytest.raises(SyntaxError):
        to_rhythm(bad)


def test_combine_wraps_pitches():
    assert combine(['c', 'e'], [F(1, 4), F(1, 4)]) == [Note('c'), Note('e')]


def test_combine_cycles_rhythm():
    events = combine(['c', 'd', 'e'], [F(1, 4), F(1, 2)])
    assert [event.duration for event in events] == [F(1, 4), F(1, 2), F(1, 4)]


def test_combine_empty_group_is_rest():
    assert combine([[], ['c']], [F(1, 2)]) == [Rest(F(1, 2)), Note('c', F(1, 2))]


def test_combine_single_group_is_note():
    assert combine([['c']], [F(1)]) == [Note('c', F(1))]


def test_combine_group_is_chord():
    events = combine([['c', 'e', 'g']], [F(1, 2)])
    assert events == [Chord(['c', 'e', 'g'], F(1, 2))]
    assert str(events[0]) == 'c4 e4 g4 1/2'


def test_combine_from_to_pitches_and_to_rhythm():
    events = combine(to_pitches('c <e g>'), to_rhythm('/4'))
    assert events == [Note('c'), Chord(['e', 'g'])]


def test_combine_rejects_empty_rhythm():
    with pytest.raises(SyntaxError):
        combine(['c'], [])
