import pytest
from fractions import Fraction as F

from solfa import (Idea, Degrees, Part, Score, SyntaxError, format_pitches,
                     deg, major_scale, minor_scale, pit, rhy)
from solfa.rhythm import (OpenMarker, CloseMarker, RestMarker, parse_rhythm,
                          format_rhythm)

SIXTH_DIM = pit('c4 d e f g ab a b c5')
PALETTES = {
    'major C': major_scale('c'),
    'major F': major_scale('f'),
    'minor A': minor_scale('a'),
    'triad': pit('d4 f a d5'),
    'sixth-dim': SIXTH_DIM,
    'pentatonic': pit('c0 d e g a c1'),
}


def names(idea):
    """Idea -> list of lists of strings, for readable asserts."""
    return [[format_pitches([[note]]) for note in group] for group in idea.content.groups]


def ev(idea):
    """events() as [(note-or-'rest', duration)], first note of each group."""
    return [('rest' if not g else format_pitches([[g[0]]]), d) for g, d in idea.events()]


def durations(idea):
    return [d for _, d in idea.events()]


# ------------------------------------------------------------ rhythm syntax

def test_rhythm_parse_basics():
    assert parse_rhythm('4 8') == [F(1, 4), F(1, 8)]
    assert parse_rhythm('1 2') == [F(1), F(1, 2)]
    assert parse_rhythm('r4') == [RestMarker(F(1, 4))]
    assert parse_rhythm('4.') == [F(3, 8)]
    assert parse_rhythm('4..') == [F(7, 16)]
    assert parse_rhythm('r4.') == [RestMarker(F(3, 8))]
    assert parse_rhythm('') == []


def test_rhythm_chains_are_one_event():
    assert parse_rhythm('4+8') == [F(3, 8)]
    assert parse_rhythm('4+8+16') == [F(7, 16)]
    assert parse_rhythm('8+8') == [F(1, 4)]
    assert parse_rhythm('r4+8') == [RestMarker(F(3, 8))]   # 'r' covers the chain
    assert parse_rhythm('4+8*2') == [F(3, 8), F(3, 8)]     # '*n' repeats the token
    assert parse_rhythm('2*5') == [F(1, 2)] * 5


def test_rhythm_groups_expand_and_nest():
    assert parse_rhythm('[4 8]') == [F(1, 4), F(1, 8)]
    assert parse_rhythm('[4 8]*2') == [F(1, 4), F(1, 8)] * 2
    # three in the time of two: the written eighths, under a 3:2 marker
    assert parse_rhythm('[3: 8 8 8]') == \
        [OpenMarker(3, 2), F(1, 8), F(1, 8), F(1, 8), CloseMarker()]
    assert parse_rhythm('[3: 8*3]') == parse_rhythm('[3: 8 8 8]')
    assert sum(d for _, d in rhy('[5: 16*5]').events()) == F(1, 4)
    assert sum(d for _, d in rhy('[7: 16*7]').events()) == F(1, 4)
    assert sum(d for _, d in rhy('[7 8: 16*7]').events()) == F(1, 2)  # '[k j:' overrides
    assert parse_rhythm('[3 2: 8 8 8]') == parse_rhythm('[3: 8 8 8]')
    nested = parse_rhythm('[3: 4 [3: 8 8 8] 4]')
    assert nested == [OpenMarker(3, 2), F(1, 4),
                      OpenMarker(3, 2), F(1, 8), F(1, 8), F(1, 8), CloseMarker(),
                      F(1, 4), CloseMarker()]
    assert sum(d for _, d in rhy('[3: 8+8]').events()) == F(1, 6)
    # a bare number after '[' is a duration, not a tuplet numerator
    assert parse_rhythm('[3 8 8 8]') == [F(1, 3), F(1, 8), F(1, 8), F(1, 8)]


def test_rhythm_open_group_cycles():
    assert parse_rhythm('4 [8') == [F(1, 4), OpenMarker(), F(1, 8)]
    assert parse_rhythm('[4 8') == [OpenMarker(), F(1, 4), F(1, 8)]
    assert parse_rhythm('[3: 8 8') == [OpenMarker(3, 2), F(1, 8), F(1, 8)]
    # nested unclosed brackets: the innermost one is the loop
    assert parse_rhythm('[3: 8 [3: 8 8') == \
        [OpenMarker(3, 2), F(1, 8), OpenMarker(3, 2), F(1, 8), F(1, 8)]
    assert parse_rhythm('4 [8 [16') == [F(1, 4), F(1, 8), OpenMarker(), F(1, 16)]


def test_rhythm_format_roundtrip():
    for text in ('4 r8 [16 2', '[3: 8 8 8]', '[7 8: 16*7]',
                 '[3: 8 8', '[3: 4 [3: 8 8 8] 4]',
                 '[3: 8 [3: 8 8', '4 [8 [16'):
        assert parse_rhythm(format_rhythm(parse_rhythm(text))) == parse_rhythm(text)


def test_rhythm_spec_examples():
    assert rhy('2*5') == rhy('2 2 2 2 2')
    assert rhy('4+8') == rhy('4.')
    assert rhy('4+8+16') == rhy('4..')
    assert rhy('8+8') == rhy('4')
    assert rhy('4+8*2') == rhy('4+8 4+8')
    assert rhy('[3: 8*3]') == rhy('[3: 8 8 8]')
    assert sum([d for _, d in (deg('1 2') @ rhy('4+4 4')).events()]) == F(3, 4)
    assert [d for _, d in (deg('1 2') @ rhy('4+4 4')).events()] == [F(1, 2), F(1, 4)]
    assert [d for _, d in (deg('1 2 3 4 5') @ rhy('8 [16')).events()] == \
        [F(1, 8), F(1, 16), F(1, 16), F(1, 16), F(1, 16)]


@pytest.mark.parametrize('text', ['0', '1/0', '0/4', 'x', 'r', '/4', '3/4', '12/8',
                                  '4|:8', '4+r8', '8]'])
def test_rhythm_illegal(text):
    with pytest.raises(SyntaxError):
        parse_rhythm(text)


def test_rhythm_errors():
    with pytest.raises(SyntaxError, match='is gone'):        # the old '|:' marker
        parse_rhythm('4 |: 8')
    with pytest.raises(SyntaxError, match='is gone'):        # the old 'a:b' tuplet
        parse_rhythm('[7:8 16*7]')
    with pytest.raises(SyntaxError, match='Nothing to cycle'):
        parse_rhythm('4 [')
    with pytest.raises(SyntaxError, match='Nothing to repeat'):
        parse_rhythm('*3')


# ---------------------------------------------------------------- two slots

def test_slots_and_compat_properties():
    i = pit('c d') @ rhy('4')
    assert isinstance(i.content, Degrees)
    assert i.content.groups == [[(1, 0)], [(2, 0)]] and i.rhythm == [F(1, 4)]
    d = deg('1 2')
    assert isinstance(d.content, Degrees)
    assert d.content.groups == [[(1, None)], [(2, None)]]
    assert rhy('4').content is None
    # indexing reads the realized events — notes and rests in play order — and
    # a slice carries the durations it actually plays
    m = pit('c d e f') @ rhy('4 [8')
    assert m[0] == m[-4] == pit('c') @ rhy('4') == m[0:1]
    assert m[1] == pit('d') @ rhy('8')
    assert m[0:2] == pit('c d') @ rhy('4 8')
    assert m[::2] == pit('c e') @ rhy('4 8')
    assert m[-2:] == pit('e f') @ rhy('8 8')
    assert m[4:9] == Idea() and m[0:0] == Idea()
    assert m.rhythm == [F(1, 4), OpenMarker(), F(1, 8)]           # the original keeps its marker
    assert len(m) == 4
    assert (m[:2] + m[2:]).events() == m.events()                # the pieces recombine
    assert [x.content.groups for x in m] == [[[(1, 0)]], [[(2, 0)]],
                                             [[(3, 0)]], [[(4, 0)]]]
    with pytest.raises(TypeError):
        m['c']
    with pytest.raises(IndexError):
        m[9]
    # a slice that lands on a rest keeps the content slot (empty), so the
    # pieces still join back with +
    t = pit('c d e') @ rhy('r4 4 r4')
    assert t[1] == pit('c') @ rhy('4')
    assert t[0].content == Degrees([]) and t[0].rhythm == [RestMarker(F(1, 4))]
    assert (t[:2] + t[2:]).events() == t.events()
    assert (t[:1] + t[1:3] + t[3:]).events() == t.events()


def test_cannot_hold_both_by_construction():
    with pytest.raises(SyntaxError):
        Idea(content=[[(1, 0)]])                   # raw lists are not content


def test_equality_and_repr():
    assert deg('1 2') == deg('1 2')
    assert deg('1 2') != deg('1 3')
    assert deg('1n') == pit('c')                   # a final natural is c4 ...
    assert deg('1') != deg('1n')                   # ... while bare waits for the palette
    assert deg('4n').content.groups == [[(4, 0)]]      # 'n' is a final natural
    assert deg('4# 4bb').content.groups == [[(4, 1)], [(4, -2)]]
    assert deg('1..5') == deg('1 2 3 4 5')         # a range is its steps
    assert deg('2,,8') == deg('2 4 6 8')           # a stepped range is its steps
    assert len(deg('1 2 3')) == 3 and len(Idea()) == 0
    assert Idea(rhythm=[]) == Idea()                       # empty rhythm is no rhythm
    assert len(rhy('4 r8')) == 2                        # a rest is one step, not two
    # an open marker is not a step: it only says where cycling starts
    assert rhy('4 [8').rhythm == [F(1, 4), OpenMarker(), F(1, 8)]


# ------------------------------------------ @ : composing (layer and stack)

def test_layering_is_symmetric_and_order_free():
    for build in (lambda: rhy('8') @ deg('1 2'),
                  lambda: deg('1 2') @ rhy('8')):
        i = build()
        assert i.content.groups == [[(1, None)], [(2, None)]] and i.rhythm == [F(1, 8)]
    i = pit('c d') @ rhy('8')
    assert i.content is not None and i.rhythm == [F(1, 8)]


def test_stacking_keeps_whichever_rhythm_exists():
    r = (deg('1 2') @ rhy('4')) @ deg('1 3')
    assert r.rhythm == [F(1, 4)]                    # the quarter stays raw and loops
    assert r.content.groups == [[(1, None)], [(3, None)], [(2, None)], [(4, None)]]
    chain = rhy('4') @ deg('1 2') @ deg('1 3')
    assert chain == r
    # stacking adds intervals; a bare accidental stays bare, but once an
    # accidental is written it is final and the sum is final too
    assert deg('2') @ deg('3') == deg('4')
    assert deg('2') @ deg('3#') == deg('4#')
    assert deg('2#') @ deg('3b') == deg('4n')
    # when both sides carry a rhythm, the right-hand one replaces the left
    assert rhy('4') @ rhy('8') == rhy('8')
    retime = (deg('1 2') @ rhy('4 [8')) @ rhy('2')
    assert retime == deg('1 2') @ rhy('2')
    stacked = (deg('1 2') @ rhy('4')) @ (deg('1 3') @ rhy('8'))
    assert stacked == deg('1 3 2 4') @ rhy('8 8')


def test_layer_and_stack_errors():
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        deg('1 2') * deg('3 4')
    with pytest.raises(SyntaxError, match=r'\* to repeat'):
        deg('1 2') @ 3
    with pytest.raises(SyntaxError, match='both sides'):
        3 @ deg('1 2')


def test_user_arpeggio_example():
    idea = rhy('8') @ deg('1 2 3') @ deg('0 1 2 3') >> pit('d4 f a d5')
    assert isinstance(idea.content, Degrees)
    assert idea.rhythm == [F(1, 8)]                 # the eighth stays raw and loops
    assert names(idea) == [['a3'], ['d4'], ['f4'], ['a4'],
                           ['d4'], ['f4'], ['a4'], ['d5'],
                           ['f4'], ['a4'], ['d5'], ['f5']]


# ---------------------------------------------------------- * : repeating

def test_repeat_without_rhythm_joins_content():
    assert (pit('c d') * 2).content.groups == pit('c d c d').content.groups
    assert (3 * pit('c')).content.groups == pit('c c c').content.groups
    assert (pit('c d') * 2).rhythm is None
    assert (pit('c d') * 1) == pit('c d')


def test_repeat_realizes_the_rhythm_once_and_loops():
    a = pit('c d') @ rhy('4 8')
    r = a * 2
    assert r.rhythm == [F(1, 4), F(1, 8)]                 # not written out per pass
    assert len(r) == 4
    assert durations(r) == [F(1, 4), F(1, 8), F(1, 4), F(1, 8)]
    # the rhythm does not grow with the count
    assert (a * 1000).rhythm == [F(1, 4), F(1, 8)] and len(a * 1000) == 2000
    # an open group inside the rhythm is unrolled for one pass, so each pass restarts it
    b = pit('c d e') @ rhy('4 [8') * 2
    assert b.rhythm == [F(1, 4), F(1, 8), F(1, 8)]
    assert durations(b) == [F(1, 4), F(1, 8), F(1, 8)] * 2


_REPEAT_NOTES = ['c', 'c d', 'c d e', 'c d e f g']
_REPEAT_RHYTHMS = ['8', '4 8', '4 [8', '4 4 r2', 'r4 4', 'r4 [4', '4 [r8 8',
                   '2 r4 4 [8 16', 'r8 4 r8', '4 r4 r8 8']


@pytest.mark.parametrize('rhythm_text', _REPEAT_RHYTHMS)
def test_repeat_is_the_same_as_concatenating_copies(rhythm_text):
    for notes in _REPEAT_NOTES:
        a = pit(notes) @ rhy(rhythm_text)
        for count in (1, 2, 3, 5):
            copies = a
            for _ in range(count - 1):
                copies = copies + a
            assert ev(a * count) == ev(copies), (notes, rhythm_text, count)


def test_repeat_leaves_the_original_alone_and_rhythm_only_stays_explicit():
    a = pit('c d') @ rhy('4 8')
    before = repr(a)
    a * 3
    assert repr(a) == before
    r = rhy('4 8') * 2                    # nothing to loop over: written out
    assert r.rhythm == [F(1, 4), F(1, 8), OpenMarker(), F(1, 4), F(1, 8)]
    assert (deg('1 2') @ rhy('4') * 3).content.groups == \
        deg('1 2 1 2 1 2').content.groups


def test_rhythm_attached_after_repeat_cycles_across_everything():
    # same notes, same rhythm, different order of operations (isorhythm vs repetition)
    each_pass = pit('c d e') @ rhy('4 8') * 2
    across = pit('c d e') * 2 @ rhy('4 8')
    assert durations(each_pass) == [F(1, 4), F(1, 8), F(1, 4)] * 2
    assert durations(across) == [F(1, 4), F(1, 8)] * 3


def test_repeat_errors():
    for bad in (0, -1, 2.5, F(1, 2), True, 'x'):
        with pytest.raises(SyntaxError):
            pit('c') * bad
    with pytest.raises(SyntaxError):
        2.5 * pit('c')


def test_repeat_resolves_like_anything_else():
    assert names(deg('1 2') * 2 >> major_scale('c')) == [['c4'], ['d4'], ['c4'], ['d4']]


# ------------------------------------------------ + : concatenation (rows)

def test_concat_neither_has_rhythm_invents_none():
    r = pit('c d') + pit('e')
    assert r.content.groups == pit('c d e').content.groups and r.rhythm is None
    assert (deg('1 2') + deg('3')).content.groups == [[(1, None)], [(2, None)], [(3, None)]]


def test_concat_both_have_rhythm_keeps_b_loop():
    a = pit('c d') @ rhy('4 8')
    b = pit('e f g') @ rhy('2 [16')
    r = a + b
    assert r.rhythm == [F(1, 4), F(1, 8), F(1, 2), OpenMarker(), F(1, 16)]
    assert ev(r) == [('c4', F(1, 4)), ('d4', F(1, 8)), ('e4', F(1, 2)),
                     ('f4', F(1, 16)), ('g4', F(1, 16))]


def test_concat_both_default_loop_b_restarts_its_own_pattern():
    a = pit('c d') @ rhy('4 8')
    b = pit('e f g') @ rhy('2 16')
    r = a + b
    assert r.rhythm == [F(1, 4), F(1, 8), OpenMarker(), F(1, 2), F(1, 16)]
    assert durations(r) == [F(1, 4), F(1, 8), F(1, 2), F(1, 16), F(1, 2)]


def test_concat_a_without_rhythm_takes_first_duration_of_b_even_a_rest():
    b = pit('e') @ rhy('r4 8')
    r = pit('c d') + b
    assert ev(r) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 4)),
                     ('e4', F(1, 8))]
    r2 = pit('c d') + pit('e') @ rhy('8 4')
    assert durations(r2)[:2] == [F(1, 8), F(1, 8)]


def test_concat_b_without_rhythm_continues_a():
    a = pit('c d e') @ rhy('4 8')
    r = a + pit('f g')
    assert r.rhythm == a.rhythm
    assert durations(r) == [F(1, 4), F(1, 8), F(1, 4), F(1, 8), F(1, 4)]


def test_concat_keeps_trailing_rests_of_a():
    a = pit('c d') @ rhy('4 4 r2')
    b = pit('e') @ rhy('8')
    r = a + b
    assert ev(r) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2)), ('e4', F(1, 8))]
    # and when b has no rhythm, a's pattern simply continues through its rest
    assert ev(a + pit('e')) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2)),
                                    ('e4', F(1, 4))]


def test_concat_rhythm_only():
    r = rhy('4 8') + rhy('2')
    assert r.rhythm == [F(1, 4), F(1, 8), OpenMarker(), F(1, 2)]
    assert r.content is None
    # a rhythm that plays only rests carries no notes, so it concatenates
    # with notes as silence
    assert ev(deg('1 2 3 4') @ rhy('4') + rhy('r4')) == \
        [('c4', F(1, 4)), ('d4', F(1, 4)), ('e4', F(1, 4)), ('f4', F(1, 4)),
         ('rest', F(1, 4))]
    assert ev(rhy('r4') + deg('1 2') @ rhy('4')) == \
        [('rest', F(1, 4)), ('c4', F(1, 4)), ('d4', F(1, 4))]
    assert ev(deg('1 2') + rhy('r4')) == \
        [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 4))]
    assert ev(rhy('r4') + deg('1 2 3 4')) == \
        [('rest', F(1, 4)), ('c4', F(1, 4)), ('d4', F(1, 4)), ('e4', F(1, 4)),
         ('f4', F(1, 4))]
    # but a rhythm with sounding steps is still ambiguous with layering
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        deg('1') + rhy('4 r8')


def test_concat_empty_idea_is_identity():
    a = pit('c d') @ rhy('4')
    assert Idea() + a == a and a + Idea() == a
    assert Idea()[:] == Idea()                            # no elements to slice
    with pytest.raises(IndexError):
        Idea()[0]


def test_concat_is_associative_when_every_part_has_rhythm():
    a = pit('c') @ rhy('4')
    b = pit('d e') @ rhy('8 16')
    c = pit('f') @ rhy('2')
    assert (a + b) + c == a + (b + c)
    assert ev((a + b) + c) == ev(a + (b + c))


def test_concat_errors():
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        rhy('4') + deg('1')
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        deg('1') + rhy('4')
    with pytest.raises(SyntaxError):
        pit('c') + 3


def test_concat_before_resolving():
    phrase = deg('1 2') @ rhy('4') + deg('5') @ rhy('2') >> major_scale('c')
    assert ev(phrase) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('g4', F(1, 2))]


# -------------------------------------------------- transpose / diatonic

def test_trans_counts_intervals_on_the_degree_line():
    m = pit('c4 e4 g4')
    assert names(m.trans('4#')) == [['f#4'], ['a#4'], ['c#5']]
    assert names(m.trans('2')) == [['d4'], ['f#4'], ['a4']]       # a second up
    assert m.trans('1') == m                                      # the unison
    assert names(m.trans('0')) == [['b3'], ['d#4'], ['f#4']]      # a second down
    assert names(m.trans('-1')) == [['a3'], ['c#4'], ['e4']]      # a third down
    # a bare degree is read as the C major spelling, and the result is final
    assert deg('1 3').trans('1') == deg('1n 3n')
    assert deg('2 3').trans('2') == deg('3n 4#')      # the second keeps its sound: E -> F#


def test_trans_accepts_a_tuple():
    m = pit('c4')
    assert m.trans((4, 1)) == m.trans('4#')


def test_trans_keeps_the_sounds():
    assert names(pit('c4').trans('4')) == [['f4']]            # a fourth up
    assert names(pit('f4').trans('4')) == [['bb4']]           # still a fourth
    assert names(pit('c4').trans('0')) == [['b3']]            # a second down
    assert names(pit('c4').trans('2', up=False)) == [['bb3']] # mirrored: a second down
    m = pit('c4 e4 g4')
    assert names(m.trans('2', up=False)) == [['bb3'], ['d4'], ['f4']]
    assert names(m.trans('-1', up=False)) == [['eb4'], ['g4'], ['bb4']]


def test_diatrans_moves_letters_and_keeps_the_accidental():
    assert names(pit('c4').diatrans(4)) == [['f4']]
    assert names(pit('f4').diatrans(4)) == [['b4']]               # letters, not sound
    assert names(pit('c4').diatrans(0)) == [['b3']]               # a letter down
    assert names(pit('c4').diatrans(2, up=False)) == [['b3']]     # mirrored: a letter down
    assert names(pit('f#4').diatrans(4)) == [['b#4']]             # the sharp rides along
    m = pit('c4 e4 g4')
    assert m.diatrans('1') == m                                       # the unison
    with pytest.raises(SyntaxError, match='whole letters'):           # no accidentals allowed
        m.diatrans('4#')
    # the scale constructors lean on diatonic; low roots must not overshoot
    assert format_pitches(major_scale('b3').content.groups) == 'b3 c#4 d#4 e4 f#4 g#4 a#4 b4'
    assert format_pitches(minor_scale('e3').content.groups) == 'e3 f#3 g3 a3 b3 c4 d4 e4'


def test_trans_keeps_rhythm_and_needs_notes():
    r = deg('1 2') @ rhy('4 8')
    assert r.trans('2').rhythm == r.rhythm
    assert r.diatrans('2').rhythm == r.rhythm
    with pytest.raises(SyntaxError, match='nothing to transpose'):
        rhy('4').trans('2')
    with pytest.raises(SyntaxError, match='nothing to transpose'):
        rhy('4').diatrans('2')
    with pytest.raises(SyntaxError, match='Illegal degree'):
        pit('c').trans('1 2')


def test_inv_diainv_and_retro():
    # diainv mirrors each degree around the low..high axis, rhythm kept
    assert deg('1 2 3 4 5').diainv('1', '5') == deg('5 4 3 2 1')
    assert deg('3#').diainv('1', '5') == deg('3b')      # the accidental mirrors too
    assert (deg('1 3') @ rhy('4 8')).diainv('1', '5') == deg('5 3') @ rhy('4 8')
    # inv keeps the sound: same number line, accidentals corrected so the
    # semitone distance is exact
    assert deg('3').diainv('1', '5') == deg('3')            # diatonic keeps the letter
    assert deg('3').inv('1', '5') == deg('3b')              # E -> Eb
    assert deg('1 2 3 4 5').inv('1', '5') == deg('5n 4n 3b 2n 1n')
    assert deg('3').inv('1', '8') == deg('6b')              # E -> Ab over the octave
    with pytest.raises(SyntaxError, match='nothing to invert'):
        rhy('4').diainv('1', '5')
    with pytest.raises(SyntaxError, match='nothing to invert'):
        rhy('4').inv('1', '5')
    with pytest.raises(SyntaxError, match='Illegal axis'):
        deg('1').diainv(3, '5')
    # retro reverses; each flag controls one layer
    assert deg('1 2 3').retro() == deg('3 2 1')
    both = deg('1 2 3') @ rhy('4 8 16')
    assert both.retro() == deg('3 2 1') @ rhy('16 8 4')
    assert both.retro(retrograde_rhythm=False) == deg('3 2 1') @ rhy('4 8 16')
    assert both.retro(retrograde_degrees=False) == deg('1 2 3') @ rhy('16 8 4')
    assert (deg('1 2') @ rhy('4 r8 16')).retro() == deg('2 1') @ rhy('16 r8 4')


# -------------------------------------------------------- events / looping

def test_events_plain_pitches_default_whole_notes():
    assert durations(pit('c d')) == [F(1), F(1)]


def test_events_whole_rhythm_loops_by_default():
    assert durations(pit('c d e') @ rhy('4 8')) == [F(1, 4), F(1, 8), F(1, 4)]
    assert durations(pit('c d e f') @ rhy('4 8')) == [F(1, 4), F(1, 8)] * 2


def test_events_open_group():
    assert durations(pit('c d e f') @ rhy('4 [8')) == [F(1, 4), F(1, 8), F(1, 8), F(1, 8)]
    assert durations(pit('c d e f') @ rhy('[4 8')) == \
        durations(pit('c d e f') @ rhy('4 8'))
    assert durations(pit('c d e f') @ rhy('4 8 [16')) == \
        [F(1, 4), F(1, 8), F(1, 16), F(1, 16)]


def test_events_with_rests_and_trailing_rest():
    assert ev(pit('c d e') @ rhy('4 r4')) == [
        ('c4', F(1, 4)), ('rest', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 4)),
        ('e4', F(1, 4)), ('rest', F(1, 4))]                  # trailing rest kept
    assert ev(pit('c d') @ rhy('4 4 r2')) == [
        ('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2))]
    assert ev(pit('c d e') @ rhy('4 4 r2')) == [      # nothing trails e
        ('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2)), ('e4', F(1, 4))]


def test_events_rest_that_begins_the_next_pass_is_not_trailing():
    assert ev(pit('c') @ rhy('r4 4')) == [('rest', F(1, 4)), ('c4', F(1, 4))]
    assert ev(pit('c d') @ rhy('r4 4')) == [
        ('rest', F(1, 4)), ('c4', F(1, 4)), ('rest', F(1, 4)), ('d4', F(1, 4))]
    assert ev(pit('c d e') @ rhy('4 [r8 8')) == [
        ('c4', F(1, 4)), ('rest', F(1, 8)), ('d4', F(1, 8)), ('rest', F(1, 8)), ('e4', F(1, 8))]
    # a rest written at the end of the pass does trail
    assert ev(pit('c d') @ rhy('4 8 r8')) == [
        ('c4', F(1, 4)), ('d4', F(1, 8)), ('rest', F(1, 8))]


def test_events_rhythm_only_plays_every_step_once():
    assert ev(rhy('4 4 r4')) == [('rest', F(1, 4))] * 3
    assert durations(rhy('4 8')) == [F(1, 4), F(1, 8)]
    # a flat rhythm-only idea indexes and slices as a list: a rest never splits
    # from its duration, an empty selection is the empty idea
    r = rhy('4 r8 16')
    assert r[0] == rhy('4') and r[-1] == rhy('16')
    assert r[1:] == rhy('r8 16') and r[:2] == rhy('4 r8')
    assert r[::-1] == rhy('16 r8 4')
    assert r[3:] == Idea()
    with pytest.raises(IndexError):
        r[9]


def test_infinite_rhythm_needs_content_or_a_slice():
    r = rhy('4 [8')
    with pytest.raises(SyntaxError, match='infinite rhythm'):
        r.events()
    with pytest.raises(SyntaxError, match='infinite rhythm'):
        rhy('[8').events()
    # a non-negative index samples the cycle forever
    assert r[0] == rhy('4') and r[1] == r[99] == rhy('8')
    # a bounded slice samples a finite window
    assert r[:2] == rhy('4 8') and r[:5] == rhy('4 8 8 8 8')
    assert r[:6:2] == rhy('4 8 8')
    # an unbounded step-1 slice keeps it cycling, so the pieces recombine
    assert r[1:] == rhy('[8')
    assert r[:1] + r[1:] == r
    # reading it from the end is meaningless
    with pytest.raises(SyntaxError):
        r[-1]
    with pytest.raises(SyntaxError):
        r[::-1]
    with pytest.raises(SyntaxError):
        r[::2]


@pytest.mark.parametrize('text', ['r4', '4 [r2', 'r4 [r8'])
def test_events_loop_without_sounding_step_raises_not_hangs(text):
    with pytest.raises(SyntaxError, match='no sounding notes'):
        (pit('c d') @ rhy(text)).events()
    # the guard fires only when the content outlasts the sounding steps: a
    # rhythm that rests after its last note still realizes
    assert durations(pit('c') @ rhy('4 [r8')) == [F(1, 4), F(1, 8)]


def test_events_degrees_resolve_through_the_base():
    # with no palette a degree is the base note (1 is c4)
    assert ev(deg('1 2') @ rhy('4')) == [('c4', F(1, 4)), ('d4', F(1, 4))]


def test_part_accepts_degrees():
    Part(deg('1 2'))
    Part(deg('1 2') >> major_scale('c'))


# --------------------------------------------------------- >> and << (palette)

def test_degrees_to_pitches():
    assert names(deg('1 2 3') >> pit('d4 f a d5')) == [['d4'], ['f4'], ['a4']]
    assert names(deg('1 4 7') >> pit('d4 f a d5')) == [['d4'], ['d5'], ['d6']]
    assert names(deg('0 -1') >> pit('d4 f a d5')) == [['a3'], ['f3']]


def test_rhythm_survives_both_directions():
    r = rhy('4 r4 [2')
    there = (deg('1 2') @ r) >> major_scale('c')
    back = there << major_scale('c')
    assert there.rhythm == back.rhythm == r.rhythm
    assert back.content.groups == [[(1, None)], [(2, None)]]    # exact notes come back bare


def test_pitches_to_degrees_chromatic_and_spelling():
    got = pit('c4 db4 c#4 d4') << major_scale('c')
    assert got.content.groups == [[(1, None)], [(2, -1)], [(1, 1)], [(2, None)]]
    assert got.content.groups[1] != got.content.groups[2]      # enharmonics stay distinct


def test_pitches_to_degrees_chords_and_octaves():
    got = pit('<c4 e g> <c5 e g>') << major_scale('c')
    assert got.content.groups == [[(1, None), (3, None), (5, None)],
                                  [(8, None), (10, None), (12, None)]]


def test_strict():
    c = major_scale('c')
    assert (pit('c d e') << c).content.groups == [[(1, None)], [(2, None)], [(3, None)]]
    with pytest.raises(SyntaxError, match='not in the palette'):
        pit('c#4').content.unmap(c.content, strict=True)
    with pytest.raises(SyntaxError, match='not in the palette'):
        pit('f4').content.unmap(PALETTES['pentatonic'].content, strict=True)


def test_no_letter_match_raises():
    p = PALETTES['pentatonic']          # c d e g a: no f, no b
    for text in ('f4', 'b4', 'f#4', 'bb3'):
        with pytest.raises(SyntaxError, match='not in the palette'):
            pit(text) << p


@pytest.mark.parametrize('name', PALETTES)
def test_pitches_roundtrip_is_exact_when_letters_match(name):
    p = PALETTES[name]
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            original = Idea(Degrees([[p.content._at((degree, acc))]]))
            assert (original << p) >> p == original, (name, degree, acc)


@pytest.mark.parametrize('name', PALETTES)
def test_degree_roundtrip_sounds_the_same(name):
    p = PALETTES[name]
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            idea = Idea(Degrees([[(degree, acc)]]))
            again = ((idea >> p) << p) >> p
            assert again == idea >> p, (name, degree, acc)


@pytest.mark.parametrize('name', ['major C', 'major F', 'minor A', 'triad'])
def test_degree_roundtrip_exact_for_distinct_letters(name):
    p = PALETTES[name]
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            idea = Idea(Degrees([[(degree, acc)]]))
            note = idea >> p
            back = note << p
            number, final = back.content.groups[0][0]
            assert number == degree, (name, degree, acc)      # the letter survives
            assert final is None or final == acc, (name, degree, acc)
            assert (back >> p) == note, (name, degree, acc)   # and so does the sound


def test_reharmonize_pipeline():
    out = pit('c e g') << major_scale('c') >> pit('d4 f a d5')
    assert names(out) == [['d4'], ['a4'], ['f5']]
    # a final accidental is final: it overrides the scale, keeping the letter
    assert (deg('4n') >> major_scale('f')).content.groups == [[(7, 0)]]   # B natural, not Bb
    assert (deg('3#') >> major_scale('eb')).content.groups == [[(5, 1)]]  # G#, not G
    assert (deg('3') >> major_scale('eb')).content.groups == [[(5, 0)]]   # bare: the scale's G


def test_each_operator_accepts_only_its_own_direction():
    c = major_scale('c')
    with pytest.raises(SyntaxError, match='nothing to map'):
        rhy('4') >> c
    with pytest.raises(SyntaxError, match='nothing to map'):
        rhy('4') << c


def test_shearing_examples():
    block = deg('1 2 3 4 5') @ deg('<1 3 5 7 9>') >> SIXTH_DIM
    assert names(block)[0] == ['c4', 'e4', 'g4', 'a4', 'c5']      # C6
    assert names(block)[1] == ['d4', 'f4', 'ab4', 'b4', 'd5']     # D dim7
    down = deg('1 2 3 4 5') @ deg('<1 -1 -3 -5>') >> SIXTH_DIM
    assert names(down)[0] == ['c4', 'a3', 'g3', 'e3']             # melody on top


def test_harmonize_example():
    def harmonize(melody):
        bebop = pit('c4 d e f g ab a b c5')
        return (pit(melody) << bebop) @ deg('<1 -1 -3 -5 -7>') >> bebop
    h = harmonize('c d e g f ab g')
    assert names(h)[0] == ['c4', 'a3', 'g3', 'e3', 'c3']          # C6, melody on top
    assert names(h)[1] == ['d4', 'b3', 'ab3', 'f3', 'd3']         # D dim7
    assert len(h) == 7
    assert len(harmonize('c d') @ rhy('4')) == 2


# ----------------------------------------------------------------- palette

def test_empty_palette_rejected():
    with pytest.raises(SyntaxError, match='Empty palette'):
        deg('1') >> pit('')


# -------------------------------------------------------------------- repr

SCOPE = {'Idea': Idea, 'pit': pit, 'deg': deg, 'rhy': rhy}


def roundtrips(idea):
    return eval(repr(idea), SCOPE) == idea


def test_repr_reads_like_the_expression_that_builds_it():
    assert repr(pit('c d e')) == "deg('1n 2n 3n')"    # pitches are final, so they print 'n'
    assert repr(deg('1 2 3')) == "deg('1 2 3')"
    assert repr(rhy('4 r4 [8')) == "rhy('4 r4 [8')"
    assert repr(pit('c d') @ rhy('4')) == "deg('1n 2n') @ rhy('4')"
    assert repr(deg('<1 3 5> 2#') @ rhy('2')) == "deg('<1 3 5> 2#') @ rhy('2')"
    assert repr(Idea()) == 'Idea()'


def test_repr_shows_the_open_marker_that_plus_inserts():
    r = pit('c d') @ rhy('4 8') + pit('e') @ rhy('2 [16')
    assert repr(r) == "deg('1n 2n 3n') @ rhy('4 8 2 [16')"


def test_repr_of_a_repeated_idea_stays_compact():
    r = pit('c d') @ rhy('4 8') * 2
    assert repr(r) == "deg('1n 2n 1n 2n') @ rhy('4 8')"


def test_repr_prefers_dotted_and_chain_durations():
    assert repr(rhy('4+8 4+8+16 8+8 1 1+1')) == "rhy('4. 4.. 4 1 1+1')"
    assert repr(rhy('5 8. 1+4')) == "rhy('5 8. 1+4')"


EXAMPLES = [
    Idea(),
    pit('c d e'),
    pit('<c4 e g> d <f a c5>'),
    pit('c#4 db4 bb3 c##5 cbb2 c-1 b#-2'),
    pit(''),
    deg('1 2 3'),
    deg('<1 3 5> -1 2# 3b 0 -7bb'),
    rhy('4 8'),
    rhy('4 r4 [8'),
    rhy('[4 8'),
    rhy('4. 2.. 1 12 2+8 7 r7 64 r8.'),
    rhy('[3: 8 8 8]'),
    rhy('[7 8: 16*7]'),
    rhy('[3: 8 8'),
    rhy('[3: 4 [3: 8 8 8] 4]'),
    rhy('[3: 8 [3: 8 8'),
    deg('1 2 3 4 5') @ rhy('[3: 8 8 8'),
    pit('c d e') @ rhy('4 r4 [8'),
    deg('1 2') @ rhy('8'),
    rhy('8') @ deg('1 2 3') @ deg('0 1 2 3'),
    (pit('c d') @ rhy('4 8')) + (pit('e f g') @ rhy('2 [16')),
    pit('c d') + pit('e') @ rhy('r4 8'),
    pit('c d e') @ rhy('4 8') * 2,
    pit('c d e') * 2 @ rhy('4 8'),
    deg('1 2') @ rhy('4') + deg('5') @ rhy('2'),
    rhy('4 8') + rhy('2'),
    deg('1 2 3 4 5') @ deg('<1 3 5 7 9>') >> SIXTH_DIM,
    deg('1 2 3 4 5') @ deg('<1 -1 -3 -5>') @ rhy('4') >> SIXTH_DIM,
    pit('c d e f g') @ rhy('8 [16'),
]


@pytest.mark.parametrize('idea', EXAMPLES, ids=repr)
def test_repr_roundtrips_through_eval(idea):
    assert roundtrips(idea)


def test_harmonize_repr_roundtrips():
    bebop = pit('c4 d e f g ab a b c5')
    h = (pit('c d e g') << bebop) @ deg('<1 -1 -3 -5 -7>') >> bebop
    assert len(h) == 4 and roundtrips(h)


@pytest.mark.parametrize('name', PALETTES)
def test_repr_roundtrips_every_pitch_the_palettes_make(name):
    p = PALETTES[name]
    for degree in range(-15, 25):
        for acc in (-2, -1, 0, 1, 2):
            single = Idea(Degrees([[p.content._at((degree, acc))]]))
            assert roundtrips(single), (name, degree, acc, repr(single))
    chord = Idea(Degrees([[p.content._at((d, a)) for d in (-3, 1, 4, 9)] for a in (-1, 0, 1)]))
    assert roundtrips(chord)


def test_repr_roundtrips_every_degree_form():
    for number in range(-20, 21):
        for acc in (-2, -1, 0, 1, 2):
            idea = Idea(Degrees([[(number, acc)], [(number, acc), (1, 0)]]))
            assert roundtrips(idea), (number, acc)


def test_repr_long_ideas_are_cut_short_and_say_so():
    long = deg(' '.join(['29'] * 20))
    text = repr(long)
    assert text.count('29') == 16 and text.endswith("… +4')")
    assert len(repr(deg(' '.join(['1'] * 500)))) < 120
    long_rhythm = repr(rhy(' '.join(['8'] * 40)))
    assert long_rhythm.count('8') == 16 and '…' in long_rhythm
    exactly = deg(' '.join(['29'] * 16))          # exactly at the limit: not cut
    assert '…' not in repr(exactly) and roundtrips(exactly)
    # a cut-short repr is for reading: it is not valid input
    with pytest.raises(SyntaxError):
        eval(text, SCOPE)


# ----------------------------------------------------------- tuplet brackets

def test_tuplet_markers_survive_the_operators():
    i = deg('1 2 3') @ rhy('[3: 8 8 8')
    assert i.rhythm == [OpenMarker(3, 2), F(1, 8), F(1, 8), F(1, 8)]
    assert durations(i) == [F(1, 12)] * 3          # written eighths, in 3:2 time
    # a slice closes the tuplet it cuts through
    cut = i[0:2]
    assert cut.rhythm == [OpenMarker(3, 2), F(1, 8), F(1, 8), CloseMarker()]
    assert durations(cut) == [F(1, 12), F(1, 12)]
    # a repeat unrolls one pass and closes the tuplet it filled
    twice = i * 2
    assert twice.rhythm == i.rhythm + [CloseMarker()]
    assert durations(twice) == [F(1, 12)] * 6
    # a sequence keeps b's own rhythm after a's unrolled one
    joined = i + (deg('4') @ rhy('4'))
    assert format_rhythm(joined.rhythm) == '[3: 8 8 8] [4'
    # retrograding keeps it a tuplet
    assert format_rhythm(i.retro().rhythm) == '[3: 8 8 8]'


def test_render_writes_tuplet_brackets(capture):
    idea = deg('1 2 3 4 5 6') @ rhy('[3: 8 8 8] 4 4 4')
    Score([Part(idea, 'X')], '4/4').show()
    xml = capture[-1]
    assert xml.count('<tuplet type="start"') == 1
    assert xml.count('<tuplet type="stop"') == 1
    assert ('<time-modification><actual-notes>3</actual-notes>'
            '<normal-notes>2</normal-notes>') in xml
    assert xml.count('<type>eighth</type>') == 3   # written type, not 1/12ths

    verovio = pytest.importorskip('verovio')
    toolkit = verovio.toolkit()
    assert toolkit.loadData(xml)
    mei = toolkit.getMEI()
    assert 'num="3"' in mei and 'numbase="2"' in mei


def test_render_numbers_nested_tuplets_and_closes_the_innermost(capture):
    idea = deg('1 2 3 4 5 6 7 8 9') @ rhy('[3: 8 8 8 [7 8: 16*7] 4')
    Score([Part(idea, 'X')], '4/4').show()
    xml = capture[-1]
    assert xml.count('<tuplet type="start"') == xml.count('<tuplet type="stop"') == 2
    assert 'number="1"' in xml and 'number="2"' in xml   # outer gets 1, inner 2
    assert '<actual-notes>7</actual-notes>' in xml       # '[k j:' ratio reaches MusicXML
    verovio = pytest.importorskip('verovio')
    assert verovio.toolkit().loadData(xml)


def test_adjacent_equal_tuplets_get_their_own_brackets(capture):
    # '[3: 8 8 8]*2' is two triplets, not one bracket spanning six eighths
    idea = deg('1 2 3 4 5 6 7 8') @ rhy('[3: 8 8 8]*2 8 8')
    Score([Part(idea, 'X')], '4/4').show()
    xml = capture[-1]
    assert xml.count('<tuplet type="start"') == 2
    assert xml.count('<tuplet type="stop"') == 2
    verovio = pytest.importorskip('verovio')
    assert verovio.toolkit().loadData(xml)
