from fractions import Fraction as F

import pytest

from complib import (Idea, major_scale, Pitch, SyntaxError, degrees, pitches, rhythm)


@pytest.mark.parametrize('name,root,accidental,octave', [
    ('c', 'c', '', 0),
    ('C', 'c', '', 0),
    ('f#4', 'f', '#', 4),
    ('bb3', 'b', 'b', 3),
    ('g##', 'g', '##', 0),
    ('e-1', 'e', '', -1),
    ('a7', 'a', '', 7),
    ('d#', 'd', '#', 0),
])
def test_pitch_parses(name, root, accidental, octave):
    pitch = Pitch(name)
    assert pitch.root() == root
    assert pitch.accidental() == accidental
    assert pitch.octave() == octave


@pytest.mark.parametrize('bad', ['h', 'cc', 'i4', 'c#b4', 'c bb'])
def test_pitch_rejects(bad):
    with pytest.raises(SyntaxError):
        Pitch(bad)


@pytest.mark.parametrize('name,midipitch', [
    ('c', 12),
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
    ('c', ['c0', 'd0', 'e0', 'f0', 'g0', 'a0', 'b0']),
    ('d', ['d0', 'e0', 'f#0', 'g0', 'a0', 'b0', 'c#1']),
    ('g', ['g0', 'a0', 'b0', 'c1', 'd1', 'e1', 'f#1']),
    ('bb', ['bb0', 'c1', 'd1', 'eb1', 'f1', 'g1', 'a1']),
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
def test_pitches(text, groups):
    assert pitches(text) == Idea(
        pitches=[[Pitch(p) for p in group] for group in groups])


@pytest.mark.parametrize('bad', ['c <e g', 'c e>', '<<c>>', '<>x', 'h', 'c <c <e>>'])
def test_pitches_rejects(bad):
    with pytest.raises(SyntaxError):
        pitches(bad)


@pytest.mark.parametrize('text,groups', [
    ('', []),
    ('1', [[(1, 0)]]),
    ('1 5', [[(1, 0)], [(5, 0)]]),
    ('<1 5>', [[(1, 0), (5, 0)]]),
    ('3b 8', [[(3, -1)], [(8, 0)]]),
    ('4#', [[(4, 1)]]),
    ('5bb 7##', [[(5, -2)], [(7, 2)]]),
    ('1 5 <3b 8> 4#', [[(1, 0)], [(5, 0)], [(3, -1), (8, 0)], [(4, 1)]]),
    ('<>', [[]]),
])
def test_degrees(text, groups):
    assert degrees(text) == Idea(degrees=groups)


@pytest.mark.parametrize('bad', ['0', '1 0', 'x', '1x', 'b', '#', '-1', '1.5', '<1 2', '1 2>', '<>x'])
def test_degrees_rejects(bad):
    with pytest.raises(SyntaxError):
        degrees(bad)


@pytest.mark.parametrize('root,text,groups', [
    ('c', '1 5 <3b 8> 4#', [['c0'], ['g0'], ['eb0', 'c1'], ['f#0']]),
    ('d', '1 5 <3b 8> 4#', [['d0'], ['a0'], ['f0', 'd1'], ['g#0']]),
    ('bb', '1 5 <3b 8> 4#', [['bb0'], ['f1'], ['db1', 'bb1'], ['e1']]),
])
def test_as_pitches(root, text, groups):
    result = degrees(text).as_pitches(major_scale(root))
    assert [[str(pitch) for pitch in group] for group in result.pitches] == groups


def test_as_pitches_keeps_rhythm():
    idea = degrees('1 5') + rhythm('/4 /8')
    result = idea.as_pitches(major_scale('c'))
    assert result.rhythm == [F(1, 4), F(1, 8)]
    assert [[str(p) for p in group] for group in result.pitches] == [['c0'], ['g0']]


def test_as_pitches_rejects_idea_without_degrees():
    with pytest.raises(SyntaxError):
        pitches('c').as_pitches(major_scale('c'))


def test_scale_degrees_beyond_octave():
    scale = major_scale('c')
    assert str(scale[8]) == 'c1'
    assert str(scale[-1]) == 'a-1'
    assert [str(pitch) for pitch in scale[4:20]] == [
        'f0', 'g0', 'a0', 'b0', 'c1', 'd1', 'e1', 'f1', 'g1', 'a1', 'b1', 'c2', 'd2', 'e2', 'f2', 'g2']


def test_scale_str_repr():
    scale = major_scale('d')
    assert str(scale) == 'd0 e0 f#0 g0 a0 b0 c#1'
    assert repr(scale) == "Scale('d0', 'c0 d0 e0 f0 g0 a0 b0')"


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
def test_rhythm(text, durations):
    assert rhythm(text) == Idea(rhythm=durations)


@pytest.mark.parametrize('bad', ['.', '/.', '1/0', '/0', 'x', '4//2', '1/4x', '/',
                                '1/', '4.5'])
def test_g_rejects(bad):
    with pytest.raises(SyntaxError):
        rhythm(bad)


def test_combine_merges_pitches_and_rhythm():
    idea = pitches('c <e g>') + rhythm('/4')
    assert idea == Idea(pitches=[[Pitch('c')], [Pitch('e'), Pitch('g')]],
                        rhythm=[F(1, 4)])


def test_combine_is_symmetric():
    melodic = pitches('c d')
    rhythmic = rhythm('/4 /8')
    assert (melodic + rhythmic) == (rhythmic + melodic)


def test_combine_empty_idea_is_identity():
    assert (Idea() + rhythm('/4')) == rhythm('/4')


def test_combine_rejects_shared_field():
    with pytest.raises(SyntaxError):
        rhythm('/4') + rhythm('/8')


def test_combine_rejects_pitches_and_degrees():
    with pytest.raises(SyntaxError):
        pitches('c') + degrees('1')
