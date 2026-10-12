import pytest
from fractions import Fraction as F

from compose import (Idea, Pitch, Palette, Pitches, Degrees, Part, SyntaxError,
                     degrees, major_scale, minor_scale, pitches, rhythm)

SIXTH_DIM = Palette('c d e f g ab a b')
PALETTES = {
    'major C': major_scale('c'),
    'major F': major_scale('f'),
    'minor A': minor_scale('a'),
    'triad': Palette('d4 f a'),
    'sixth-dim': SIXTH_DIM,
    'pentatonic': Palette('c0 d e g a'),
}


def names(idea):
    """Idea with pitches -> list of lists of strings, for readable asserts."""
    return [[str(p) for p in group] for group in idea.pitches]


# ---------------------------------------------------------------- two slots

def test_slots_and_compat_properties():
    i = pitches('c d') + rhythm('/4')
    assert isinstance(i.content, Pitches)
    assert i.pitches == i.content.groups and i.degrees is None
    d = degrees('1 2')
    assert isinstance(d.content, Degrees)
    assert d.degrees == [[(1, 0)], [(2, 0)]] and d.pitches is None
    assert rhythm('/4').content is None


def test_cannot_hold_both_by_construction():
    with pytest.raises(SyntaxError):
        Idea(content=[[Pitch('c')]])          # raw lists are not content


def test_add_fills_each_slot_once():
    assert (degrees('1') + rhythm('/4')).rhythm == [F(1, 4)]
    with pytest.raises(SyntaxError, match='share degrees'):
        degrees('1') + degrees('2')
    with pytest.raises(SyntaxError, match='share pitches'):
        pitches('c') + pitches('d')
    with pytest.raises(SyntaxError, match='share rhythm'):
        rhythm('/4') + rhythm('/8')
    with pytest.raises(SyntaxError, match='both pitches and degrees'):
        pitches('c') + degrees('1')
    with pytest.raises(SyntaxError):
        pitches('c') + 3


def test_equality_and_repr():
    assert degrees('1 2') == degrees('1 2')
    assert degrees('1 2') != degrees('1 3')
    assert degrees('1') != pitches('c')
    assert repr(degrees('1') + rhythm('/4')) == \
        "Idea(degrees=[[(1, 0)]], rhythm=[Fraction(1, 4)])"
    assert len(degrees('1 2 3')) == 3 and len(rhythm('/4 /4')) == 2 and len(Idea()) == 0


def test_stack_errors():
    with pytest.raises(SyntaxError, match='share rhythm'):
        (degrees('1') + rhythm('/4')) * (degrees('1') + rhythm('/8'))
    with pytest.raises(SyntaxError, match="don't have degrees"):
        pitches('c') * degrees('1')
    with pytest.raises(SyntaxError, match="don't have degrees"):
        degrees('1') * rhythm('/4')


def test_stack_keeps_whichever_rhythm_exists():
    r = (degrees('1 2') + rhythm('/4')) * degrees('1 3')
    assert r.rhythm == [F(1, 4)]
    assert r.degrees == [[(1, 0)], [(2, 0)], [(3, 0)], [(4, 0)]]


# ----------------------------------------------------------- >> / against

def test_degrees_to_pitches():
    assert names(degrees('1 2 3') >> Palette('d4 f a')) == [['d4'], ['f4'], ['a4']]
    assert names(degrees('1 4 7') >> Palette('d4 f a')) == [['d4'], ['d5'], ['d6']]
    assert names(degrees('0 -1') >> Palette('d4 f a')) == [['a3'], ['f3']]


def test_user_arpeggio_example():
    idea = rhythm('/8') + degrees('1 2 3') * degrees('0 1 2 3') >> Palette('d4 f a')
    assert isinstance(idea.content, Pitches)
    assert idea.rhythm == [F(1, 8)]
    assert names(idea) == [['a3'], ['d4'], ['f4'], ['d4'], ['f4'], ['a4'],
                           ['f4'], ['a4'], ['d5'], ['a4'], ['d5'], ['f5']]


def test_rhythm_survives_both_directions():
    r = rhythm('/4 _/4 /2')
    there = (degrees('1 2') + r) >> major_scale('c')
    back = there >> major_scale('c')
    assert there.rhythm == back.rhythm == r.rhythm
    assert back.degrees == [[(1, 0)], [(2, 0)]]


def test_pitches_to_degrees_chromatic_and_spelling():
    got = pitches('c4 db4 c#4 d4') >> major_scale('c')
    assert got.degrees == [[(1, 0)], [(2, -1)], [(1, 1)], [(2, 0)]]
    # enharmonic spellings stay distinct
    assert got.degrees[1] != got.degrees[2]


def test_pitches_to_degrees_chords_and_octaves():
    got = pitches('<c4 e g> <c5 e g>') >> major_scale('c')
    assert got.degrees == [[(1, 0), (3, 0), (5, 0)], [(8, 0), (10, 0), (12, 0)]]


def test_strict():
    c = major_scale('c')
    assert (pitches('c d e') >> c) == pitches('c d e').as_degrees(c, strict=True)
    with pytest.raises(SyntaxError, match='not in the palette'):
        pitches('c#4').as_degrees(c, strict=True)
    with pytest.raises(SyntaxError, match='not in the palette'):
        pitches('f4').as_degrees(PALETTES['pentatonic'], strict=True)


def test_no_letter_match_falls_back_to_nearest_sound():
    p = PALETTES['pentatonic']          # c d e g a: no f, no b
    for text in ('f4', 'b4', 'f#4', 'bb3'):
        idea = pitches(text)
        back = (idea >> p) >> p
        assert back.pitches[0][0].midipitch() == idea.pitches[0][0].midipitch()


@pytest.mark.parametrize('name', PALETTES)
def test_pitches_roundtrip_is_exact_when_letters_match(name):
    p = PALETTES[name]
    # every pitch in a wide range, with accidentals, whose letter is in the palette
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            original = Idea(Pitches([[p.at(degree, acc)]]))
            assert (original >> p) >> p == original, (name, degree, acc)


@pytest.mark.parametrize('name', PALETTES)
def test_degree_roundtrip_sounds_the_same(name):
    p = PALETTES[name]
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            idea = Idea(Degrees([[(degree, acc)]]))
            again = ((idea >> p) >> p) >> p
            assert again == idea >> p, (name, degree, acc)


@pytest.mark.parametrize('name', ['major C', 'major F', 'minor A', 'triad'])
def test_degree_roundtrip_exact_for_distinct_letters(name):
    p = PALETTES[name]
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            idea = Idea(Degrees([[(degree, acc)]]))
            assert (idea >> p) >> p == idea, (name, degree, acc)


def test_reharmonize():
    melody = pitches('c e g')
    out = melody >> major_scale('c') >> Palette('d4 f a')
    assert names(out) == [['d4'], ['a4'], ['f5']]


def test_rshift_errors():
    with pytest.raises(SyntaxError, match='expected a Palette'):
        degrees('1') >> 3
    with pytest.raises(SyntaxError, match='nothing to resolve'):
        rhythm('/4') >> major_scale('c')
    with pytest.raises(SyntaxError, match='without degrees'):
        pitches('c').as_pitches(major_scale('c'))
    with pytest.raises(SyntaxError, match='without pitches'):
        degrees('1').as_degrees(major_scale('c'))


def test_empty_chord_passes_through():
    both = pitches('c <> d') >> major_scale('c')
    assert both.degrees == [[(1, 0)], [], [(2, 0)]]
    assert (both >> major_scale('c')).pitches[1] == []


def test_shearing_examples():
    block = degrees('1 2 3 4 5') * degrees('<1 3 5 7 9>') >> SIXTH_DIM
    assert names(block)[0] == ['c4', 'e4', 'g4', 'a4', 'c5']      # C6
    assert names(block)[1] == ['d4', 'f4', 'ab4', 'b4', 'd5']     # D dim7
    down = degrees('1 2 3 4 5') * degrees('<1 -1 -3 -5>') >> SIXTH_DIM
    assert names(down)[0] == ['c4', 'a3', 'g3', 'e3']             # melody on top


# ------------------------------------------------------------------ events

def test_events_plain_pitches_default_whole_notes():
    ev = pitches('c d').events()
    assert [d for _, d in ev] == [F(1), F(1)]


def test_events_rhythm_cycles_over_pitches():
    ev = (pitches('c d e') + rhythm('/4 /8')).events()
    assert [d for _, d in ev] == [F(1, 4), F(1, 8), F(1, 4)]


def test_events_with_rests():
    ev = (pitches('c d e') + rhythm('/4 _/4')).events()
    assert [(bool(g), d) for g, d in ev] == [
        (True, F(1, 4)), (False, F(1, 4)), (True, F(1, 4)),
        (False, F(1, 4)), (True, F(1, 4))]


def test_events_rhythm_only_ending_in_rest_terminates():
    ev = rhythm('/4 /4 _/4').events()
    assert [(bool(g), d) for g, d in ev] == [(False, F(1, 4))] * 3


def test_events_all_rest_rhythm_with_pitches_raises_not_hangs():
    with pytest.raises(SyntaxError, match='no sounding notes'):
        (pitches('c d') + rhythm('_/4')).events()


def test_part_still_rejects_degrees():
    with pytest.raises(SyntaxError):
        Part(degrees('1 2'))
    Part(degrees('1 2') >> major_scale('c'))


# ----------------------------------------------------------------- palette

def test_empty_palette_rejected():
    with pytest.raises(SyntaxError, match='Empty palette'):
        Palette('')
