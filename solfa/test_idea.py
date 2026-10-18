import pytest
from fractions import Fraction as F

from solfa import (Idea, Degrees, Part, SyntaxError, format_pitches,
                     degrees, major_scale, minor_scale, pitches, rhythm)
from solfa.rhythm import (LOOP_MARKER, REST_MARKER, parse_rhythm,
                            rhythm_from_steps, rhythm_steps)

SIXTH_DIM = pitches('c4 d e f g ab a b c5').content
PALETTES = {
    'major C': major_scale('c'),
    'major F': major_scale('f'),
    'minor A': minor_scale('a'),
    'triad': pitches('d4 f a d5').content,
    'sixth-dim': SIXTH_DIM,
    'pentatonic': pitches('c0 d e g a c1').content,
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
    assert parse_rhythm('r4') == [REST_MARKER, F(1, 4)]
    assert parse_rhythm('3/4') == [F(3, 4)]
    assert parse_rhythm('12/8') == [F(3, 2)]            # multi-digit numerator
    assert parse_rhythm('4.') == [F(3, 8)]
    assert parse_rhythm('4..') == [F(7, 16)]
    assert parse_rhythm('r4.') == [REST_MARKER, F(3, 8)]


def test_rhythm_loop_marker_parse():
    assert parse_rhythm('4 |: 8') == [F(1, 4), LOOP_MARKER, F(1, 8)]
    assert parse_rhythm('|: 4 8') == [LOOP_MARKER, F(1, 4), F(1, 8)]


@pytest.mark.parametrize('text', ['0', '1/0', '0/4', 'x', 'r', '/4', '4|:8', '4 |:'])
def test_rhythm_illegal(text):
    with pytest.raises(SyntaxError):
        parse_rhythm(text)


def test_rhythm_loop_marker_errors():
    with pytest.raises(SyntaxError, match='Only one loop marker'):
        parse_rhythm('4 |: 8 |: 16')
    with pytest.raises(SyntaxError, match='runs to the end'):
        parse_rhythm('4 8 :|')
    with pytest.raises(SyntaxError, match='Nothing to loop'):
        parse_rhythm('4 |:')


def test_rhythm_steps_roundtrip():
    r = parse_rhythm('4 r8 |: 16 2')
    steps, loop = rhythm_steps(r)
    assert steps == [(False, F(1, 4)), (True, F(1, 8)), (False, F(1, 16)), (False, F(1, 2))]
    assert loop == 2
    assert rhythm_from_steps(steps, loop) == r
    # the default loop (everything) is written without a marker
    assert rhythm_from_steps(steps, 0) == parse_rhythm('4 r8 16 2')


# ---------------------------------------------------------------- two slots

def test_slots_and_compat_properties():
    i = pitches('c d') @ rhythm('4')
    assert isinstance(i.content, Degrees)
    assert i.content.groups == [[(1, 0)], [(2, 0)]] and i.rhythm == [F(1, 4)]
    d = degrees('1 2')
    assert isinstance(d.content, Degrees)
    assert d.content.groups == [[(1, 0)], [(2, 0)]]
    assert rhythm('4').content is None
    # indexing reads the realized events — notes and rests in play order — and
    # a slice carries the durations it actually plays
    m = pitches('c d e f') @ rhythm('4 |: 8')
    assert m[0] == m[-4] == pitches('c') @ rhythm('4') == m[0:1]
    assert m[1] == pitches('d') @ rhythm('8')
    assert m[0:2] == pitches('c d') @ rhythm('4 8')
    assert m[::2] == pitches('c e') @ rhythm('4 8')
    assert m[-2:] == pitches('e f') @ rhythm('8 8')
    assert m[4:9] == Idea() and m[0:0] == Idea()
    assert m.rhythm == [F(1, 4), LOOP_MARKER, F(1, 8)]           # the original keeps its marker
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
    t = pitches('c d e') @ rhythm('r4 4 r4')
    assert t[1] == pitches('c') @ rhythm('4')
    assert t[0].content == Degrees([]) and t[0].rhythm == ['r', F(1, 4)]
    assert (t[:2] + t[2:]).events() == t.events()
    assert (t[:1] + t[1:3] + t[3:]).events() == t.events()


def test_cannot_hold_both_by_construction():
    with pytest.raises(SyntaxError):
        Idea(content=[[(1, 0)]])                   # raw lists are not content


def test_equality_and_repr():
    assert degrees('1 2') == degrees('1 2')
    assert degrees('1 2') != degrees('1 3')
    assert degrees('1') == pitches('c')                    # degree 1 is c4
    assert len(degrees('1 2 3')) == 3 and len(Idea()) == 0
    assert Idea(rhythm=[]) == Idea()                       # empty rhythm is no rhythm
    assert len(rhythm('4 r8')) == 2                        # a rest is one step, not two
    assert len(rhythm('4 |: 8')) == 2                      # a loop marker is not a step


# ------------------------------------------ @ : composing (layer and stack)

def test_layering_is_symmetric_and_order_free():
    for build in (lambda: rhythm('8') @ degrees('1 2'),
                  lambda: degrees('1 2') @ rhythm('8')):
        i = build()
        assert i.content.groups == [[(1, 0)], [(2, 0)]] and i.rhythm == [F(1, 8)]
    i = pitches('c d') @ rhythm('8')
    assert i.content is not None and i.rhythm == [F(1, 8)]


def test_stacking_keeps_whichever_rhythm_exists():
    r = (degrees('1 2') @ rhythm('4')) @ degrees('1 3')
    assert r.rhythm == [F(1, 4), F(1, 4)]        # the quarter realized over the two notes
    assert r.content.groups == [[(1, 0)], [(2, 0)], [(3, 0)], [(4, 0)]]
    chain = rhythm('4') @ degrees('1 2') @ degrees('1 3')
    assert chain == r


def test_layer_and_stack_errors():
    with pytest.raises(SyntaxError, match='share rhythm'):
        (degrees('1') @ rhythm('4')) @ (degrees('1') @ rhythm('8'))
    with pytest.raises(SyntaxError, match='share rhythm'):
        rhythm('4') @ rhythm('8')
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        degrees('1 2') * degrees('3 4')
    with pytest.raises(SyntaxError, match=r'\* to repeat'):
        degrees('1 2') @ 3
    with pytest.raises(SyntaxError, match='both sides'):
        3 @ degrees('1 2')


def test_user_arpeggio_example():
    idea = rhythm('8') @ degrees('1 2 3') @ degrees('0 1 2 3') >> pitches('d4 f a d5')
    assert isinstance(idea.content, Degrees)
    assert idea.rhythm == [F(1, 8), F(1, 8), F(1, 8)]
    assert names(idea) == [['a3'], ['d4'], ['f4'], ['d4'], ['f4'], ['a4'],
                           ['f4'], ['a4'], ['d5'], ['a4'], ['d5'], ['f5']]


# ---------------------------------------------------------- * : repeating

def test_repeat_without_rhythm_joins_content():
    assert (pitches('c d') * 2).content.groups == pitches('c d c d').content.groups
    assert (3 * pitches('c')).content.groups == pitches('c c c').content.groups
    assert (pitches('c d') * 2).rhythm is None
    assert (pitches('c d') * 1) == pitches('c d')


def test_repeat_realizes_the_rhythm_once_and_loops():
    a = pitches('c d') @ rhythm('4 8')
    r = a * 2
    assert r.rhythm == [F(1, 4), F(1, 8)]                 # not written out per pass
    assert len(r) == 4
    assert durations(r) == [F(1, 4), F(1, 8), F(1, 4), F(1, 8)]
    # the rhythm does not grow with the count
    assert (a * 1000).rhythm == [F(1, 4), F(1, 8)] and len(a * 1000) == 2000
    # a loop marker inside the rhythm is unrolled for one pass, so each pass restarts it
    b = pitches('c d e') @ rhythm('4 |: 8') * 2
    assert b.rhythm == [F(1, 4), F(1, 8), F(1, 8)]
    assert durations(b) == [F(1, 4), F(1, 8), F(1, 8)] * 2


_REPEAT_NOTES = ['c', 'c d', 'c d e', 'c d e f g']
_REPEAT_RHYTHMS = ['8', '4 8', '4 |: 8', '4 4 r2', 'r4 4', 'r4 |: 4', '4 |: r8 8',
                   '2 r4 4 |: 8 16', 'r8 4 r8', '4 r4 r8 8']


@pytest.mark.parametrize('rhythm_text', _REPEAT_RHYTHMS)
def test_repeat_is_the_same_as_concatenating_copies(rhythm_text):
    for notes in _REPEAT_NOTES:
        a = pitches(notes) @ rhythm(rhythm_text)
        for count in (1, 2, 3, 5):
            copies = a
            for _ in range(count - 1):
                copies = copies + a
            assert ev(a * count) == ev(copies), (notes, rhythm_text, count)


def test_repeat_leaves_the_original_alone_and_rhythm_only_stays_explicit():
    a = pitches('c d') @ rhythm('4 8')
    before = repr(a)
    a * 3
    assert repr(a) == before
    r = rhythm('4 8') * 2                    # nothing to loop over: written out
    assert r.rhythm == [F(1, 4), F(1, 8), LOOP_MARKER, F(1, 4), F(1, 8)]
    assert (degrees('1 2') @ rhythm('4') * 3).content.groups == \
        degrees('1 2 1 2 1 2').content.groups


def test_rhythm_attached_after_repeat_cycles_across_everything():
    # same notes, same rhythm, different order of operations (isorhythm vs repetition)
    each_pass = pitches('c d e') @ rhythm('4 8') * 2
    across = pitches('c d e') * 2 @ rhythm('4 8')
    assert durations(each_pass) == [F(1, 4), F(1, 8), F(1, 4)] * 2
    assert durations(across) == [F(1, 4), F(1, 8)] * 3


def test_repeat_errors():
    for bad in (0, -1, 2.5, F(1, 2), True, 'x'):
        with pytest.raises(SyntaxError):
            pitches('c') * bad
    with pytest.raises(SyntaxError):
        2.5 * pitches('c')


def test_repeat_resolves_like_anything_else():
    assert names(degrees('1 2') * 2 >> major_scale('c')) == [['c4'], ['d4'], ['c4'], ['d4']]


# ------------------------------------------------ + : concatenation (rows)

def test_concat_neither_has_rhythm_invents_none():
    r = pitches('c d') + pitches('e')
    assert r.content.groups == pitches('c d e').content.groups and r.rhythm is None
    assert (degrees('1 2') + degrees('3')).content.groups == [[(1, 0)], [(2, 0)], [(3, 0)]]


def test_concat_both_have_rhythm_keeps_b_loop():
    a = pitches('c d') @ rhythm('4 8')
    b = pitches('e f g') @ rhythm('2 |: 16')
    r = a + b
    assert r.rhythm == [F(1, 4), F(1, 8), F(1, 2), LOOP_MARKER, F(1, 16)]
    assert ev(r) == [('c4', F(1, 4)), ('d4', F(1, 8)), ('e4', F(1, 2)),
                     ('f4', F(1, 16)), ('g4', F(1, 16))]


def test_concat_both_default_loop_b_restarts_its_own_pattern():
    a = pitches('c d') @ rhythm('4 8')
    b = pitches('e f g') @ rhythm('2 16')
    r = a + b
    assert r.rhythm == [F(1, 4), F(1, 8), LOOP_MARKER, F(1, 2), F(1, 16)]
    assert durations(r) == [F(1, 4), F(1, 8), F(1, 2), F(1, 16), F(1, 2)]


def test_concat_a_without_rhythm_takes_first_duration_of_b_even_a_rest():
    b = pitches('e') @ rhythm('r4 8')
    r = pitches('c d') + b
    assert ev(r) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 4)),
                     ('e4', F(1, 8))]
    r2 = pitches('c d') + pitches('e') @ rhythm('8 4')
    assert durations(r2)[:2] == [F(1, 8), F(1, 8)]


def test_concat_b_without_rhythm_continues_a():
    a = pitches('c d e') @ rhythm('4 8')
    r = a + pitches('f g')
    assert r.rhythm == a.rhythm
    assert durations(r) == [F(1, 4), F(1, 8), F(1, 4), F(1, 8), F(1, 4)]


def test_concat_keeps_trailing_rests_of_a():
    a = pitches('c d') @ rhythm('4 4 r2')
    b = pitches('e') @ rhythm('8')
    r = a + b
    assert ev(r) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2)), ('e4', F(1, 8))]
    # and when b has no rhythm, a's pattern simply continues through its rest
    assert ev(a + pitches('e')) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2)),
                                    ('e4', F(1, 4))]


def test_concat_rhythm_only():
    r = rhythm('4 8') + rhythm('2')
    assert r.rhythm == [F(1, 4), F(1, 8), LOOP_MARKER, F(1, 2)]
    assert r.content is None
    # a rhythm that plays only rests carries no notes, so it concatenates
    # with notes as silence
    assert ev(degrees('1 2 3 4') @ rhythm('4') + rhythm('r4')) == \
        [('c4', F(1, 4)), ('d4', F(1, 4)), ('e4', F(1, 4)), ('f4', F(1, 4)),
         ('rest', F(1, 4))]
    assert ev(rhythm('r4') + degrees('1 2') @ rhythm('4')) == \
        [('rest', F(1, 4)), ('c4', F(1, 4)), ('d4', F(1, 4))]
    assert ev(degrees('1 2') + rhythm('r4')) == \
        [('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 4))]
    assert ev(rhythm('r4') + degrees('1 2 3 4')) == \
        [('rest', F(1, 4)), ('c4', F(1, 4)), ('d4', F(1, 4)), ('e4', F(1, 4)),
         ('f4', F(1, 4))]
    # but a rhythm with sounding steps is still ambiguous with layering
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        degrees('1') + rhythm('4 r8')


def test_concat_empty_idea_is_identity():
    a = pitches('c d') @ rhythm('4')
    assert Idea() + a == a and a + Idea() == a
    assert Idea()[:] == Idea()                            # no elements to slice
    with pytest.raises(IndexError):
        Idea()[0]


def test_concat_is_associative_when_every_part_has_rhythm():
    a = pitches('c') @ rhythm('4')
    b = pitches('d e') @ rhythm('8 16')
    c = pitches('f') @ rhythm('2')
    assert (a + b) + c == a + (b + c)
    assert ev((a + b) + c) == ev(a + (b + c))


def test_concat_errors():
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        rhythm('4') + degrees('1')
    with pytest.raises(SyntaxError, match=r'use @ to compose'):
        degrees('1') + rhythm('4')
    with pytest.raises(SyntaxError):
        pitches('c') + 3


def test_concat_before_resolving():
    phrase = degrees('1 2') @ rhythm('4') + degrees('5') @ rhythm('2') >> major_scale('c')
    assert ev(phrase) == [('c4', F(1, 4)), ('d4', F(1, 4)), ('g4', F(1, 2))]


# -------------------------------------------------- transpose / diatonic

def test_transpose_counts_intervals_on_the_degree_line():
    m = pitches('c4 e4 g4')
    assert names(m.transpose('4#')) == [['f#4'], ['a#4'], ['c#5']]
    assert names(m.transpose('2')) == [['d4'], ['f#4'], ['a4']]       # a second up
    assert m.transpose('1') == m                                      # the unison
    assert names(m.transpose('0')) == [['b3'], ['d#4'], ['f#4']]      # a second down
    assert names(m.transpose('-1')) == [['a3'], ['c#4'], ['e4']]      # a third down


def test_transpose_accepts_a_tuple():
    m = pitches('c4')
    assert m.transpose((4, 1)) == m.transpose('4#')


def test_transpose_keeps_the_sounds():
    assert names(pitches('c4').transpose('4')) == [['f4']]            # a fourth up
    assert names(pitches('f4').transpose('4')) == [['bb4']]           # still a fourth
    assert names(pitches('c4').transpose('0')) == [['b3']]            # a second down
    assert names(pitches('c4').transpose('2', up=False)) == [['bb3']] # mirrored: a second down
    m = pitches('c4 e4 g4')
    assert names(m.transpose('2', up=False)) == [['bb3'], ['d4'], ['f4']]
    assert names(m.transpose('-1', up=False)) == [['eb4'], ['g4'], ['bb4']]


def test_diatonic_moves_letters_and_keeps_the_accidental():
    assert names(pitches('c4').diatonic(4)) == [['f4']]
    assert names(pitches('f4').diatonic(4)) == [['b4']]               # letters, not sound
    assert names(pitches('c4').diatonic(0)) == [['b3']]               # a letter down
    assert names(pitches('c4').diatonic(2, up=False)) == [['b3']]     # mirrored: a letter down
    assert names(pitches('f#4').diatonic(4)) == [['b#4']]             # the sharp rides along
    m = pitches('c4 e4 g4')
    assert m.diatonic('1') == m                                       # the unison
    with pytest.raises(SyntaxError, match='whole letters'):           # no accidentals allowed
        m.diatonic('4#')
    # the scale constructors lean on diatonic; low roots must not overshoot
    assert format_pitches(major_scale('b3').groups) == 'b3 c#4 d#4 e4 f#4 g#4 a#4 b4'
    assert format_pitches(minor_scale('e3').groups) == 'e3 f#3 g3 a3 b3 c4 d4 e4'


def test_transpose_keeps_rhythm_and_needs_notes():
    r = degrees('1 2') @ rhythm('4 8')
    assert r.transpose('2').rhythm == r.rhythm
    assert r.diatonic('2').rhythm == r.rhythm
    with pytest.raises(SyntaxError, match='nothing to transpose'):
        rhythm('4').transpose('2')
    with pytest.raises(SyntaxError, match='nothing to transpose'):
        rhythm('4').diatonic('2')
    with pytest.raises(SyntaxError, match='Illegal degree'):
        pitches('c').transpose('1 2')


# -------------------------------------------------------- events / looping

def test_events_plain_pitches_default_whole_notes():
    assert durations(pitches('c d')) == [F(1), F(1)]


def test_events_whole_rhythm_loops_by_default():
    assert durations(pitches('c d e') @ rhythm('4 8')) == [F(1, 4), F(1, 8), F(1, 4)]
    assert durations(pitches('c d e f') @ rhythm('4 8')) == [F(1, 4), F(1, 8)] * 2


def test_events_loop_marker():
    assert durations(pitches('c d e f') @ rhythm('4 |: 8')) == [F(1, 4), F(1, 8), F(1, 8), F(1, 8)]
    assert durations(pitches('c d e f') @ rhythm('|: 4 8')) == \
        durations(pitches('c d e f') @ rhythm('4 8'))
    assert durations(pitches('c d e f') @ rhythm('4 8 |: 16')) == \
        [F(1, 4), F(1, 8), F(1, 16), F(1, 16)]


def test_events_with_rests_and_trailing_rest():
    assert ev(pitches('c d e') @ rhythm('4 r4')) == [
        ('c4', F(1, 4)), ('rest', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 4)),
        ('e4', F(1, 4)), ('rest', F(1, 4))]                  # trailing rest kept
    assert ev(pitches('c d') @ rhythm('4 4 r2')) == [
        ('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2))]
    assert ev(pitches('c d e') @ rhythm('4 4 r2')) == [      # nothing trails e
        ('c4', F(1, 4)), ('d4', F(1, 4)), ('rest', F(1, 2)), ('e4', F(1, 4))]


def test_events_rest_that_begins_the_next_pass_is_not_trailing():
    assert ev(pitches('c') @ rhythm('r4 4')) == [('rest', F(1, 4)), ('c4', F(1, 4))]
    assert ev(pitches('c d') @ rhythm('r4 4')) == [
        ('rest', F(1, 4)), ('c4', F(1, 4)), ('rest', F(1, 4)), ('d4', F(1, 4))]
    assert ev(pitches('c d e') @ rhythm('4 |: r8 8')) == [
        ('c4', F(1, 4)), ('rest', F(1, 8)), ('d4', F(1, 8)), ('rest', F(1, 8)), ('e4', F(1, 8))]
    # a rest written at the end of the pass does trail
    assert ev(pitches('c d') @ rhythm('4 8 r8')) == [
        ('c4', F(1, 4)), ('d4', F(1, 8)), ('rest', F(1, 8))]


def test_events_rhythm_only_plays_every_step_once():
    assert ev(rhythm('4 4 r4')) == [('rest', F(1, 4))] * 3
    assert durations(rhythm('4 |: 8')) == [F(1, 4), F(1, 8)]
    # a rhythm-only idea indexes its steps as they play — a rest never splits
    # from its duration — and a slice drops the loop marker: it just plays the
    # durations it carries, while + puts the marker back at the join
    r = rhythm('4 r8 |: 16')
    assert r[0] == rhythm('4') and r[-1] == rhythm('16')
    assert r[1:] == rhythm('r8 16') and r[:2] == rhythm('4 r8')
    assert r[::-1] == rhythm('16 r8 4')
    assert r[:2] + r[2:] == r
    assert r[3:] == Idea()
    with pytest.raises(IndexError):
        r[9]


@pytest.mark.parametrize('text', ['r4', '4 |: r2', 'r4 |: r8'])
def test_events_loop_without_sounding_step_raises_not_hangs(text):
    with pytest.raises(SyntaxError, match='no sounding notes'):
        (pitches('c d') @ rhythm(text)).events()
    # the guard fires only when the content outlasts the sounding steps: a
    # rhythm that rests after its last note still realizes
    assert durations(pitches('c') @ rhythm('4 |: r8')) == [F(1, 4), F(1, 8)]


def test_events_degrees_resolve_through_the_base():
    # with no palette a degree is the base note (1 is c4)
    assert ev(degrees('1 2') @ rhythm('4')) == [('c4', F(1, 4)), ('d4', F(1, 4))]


def test_part_accepts_degrees():
    Part(degrees('1 2'))
    Part(degrees('1 2') >> major_scale('c'))


# --------------------------------------------------------- >> and << (palette)

def test_degrees_to_pitches():
    assert names(degrees('1 2 3') >> pitches('d4 f a d5')) == [['d4'], ['f4'], ['a4']]
    assert names(degrees('1 4 7') >> pitches('d4 f a d5')) == [['d4'], ['d5'], ['d6']]
    assert names(degrees('0 -1') >> pitches('d4 f a d5')) == [['a3'], ['f3']]


def test_rhythm_survives_both_directions():
    r = rhythm('4 r4 |: 2')
    there = (degrees('1 2') @ r) >> major_scale('c')
    back = there << major_scale('c')
    assert there.rhythm == back.rhythm == r.rhythm
    assert back.content.groups == [[(1, 0)], [(2, 0)]]


def test_pitches_to_degrees_chromatic_and_spelling():
    got = pitches('c4 db4 c#4 d4') << major_scale('c')
    assert got.content.groups == [[(1, 0)], [(2, -1)], [(1, 1)], [(2, 0)]]
    assert got.content.groups[1] != got.content.groups[2]      # enharmonics stay distinct


def test_pitches_to_degrees_chords_and_octaves():
    got = pitches('<c4 e g> <c5 e g>') << major_scale('c')
    assert got.content.groups == [[(1, 0), (3, 0), (5, 0)], [(8, 0), (10, 0), (12, 0)]]


def test_strict():
    c = major_scale('c')
    assert (pitches('c d e') << c).content.groups == [[(1, 0)], [(2, 0)], [(3, 0)]]
    with pytest.raises(SyntaxError, match='not in the palette'):
        pitches('c#4').content.decompose(c, strict=True)
    with pytest.raises(SyntaxError, match='not in the palette'):
        pitches('f4').content.decompose(PALETTES['pentatonic'], strict=True)


def test_no_letter_match_raises():
    p = PALETTES['pentatonic']          # c d e g a: no f, no b
    for text in ('f4', 'b4', 'f#4', 'bb3'):
        with pytest.raises(SyntaxError, match='not in the palette'):
            pitches(text) << p


@pytest.mark.parametrize('name', PALETTES)
def test_pitches_roundtrip_is_exact_when_letters_match(name):
    p = PALETTES[name]
    for degree in range(-25, 40):
        for acc in (-1, 0, 1):
            original = Idea(Degrees([[p._at((degree, acc))]]))
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
            assert (idea >> p) << p == idea, (name, degree, acc)


def test_reharmonize_pipeline():
    out = pitches('c e g') << major_scale('c') >> pitches('d4 f a d5')
    assert names(out) == [['d4'], ['a4'], ['f5']]


def test_each_operator_accepts_only_its_own_direction():
    c = major_scale('c')
    with pytest.raises(SyntaxError, match='expected degrees'):
        degrees('1') >> 3
    with pytest.raises(SyntaxError, match='nothing to resolve'):
        rhythm('4') >> c
    with pytest.raises(SyntaxError, match='nothing to resolve'):
        rhythm('4') << c


def test_shearing_examples():
    block = degrees('1 2 3 4 5') @ degrees('<1 3 5 7 9>') >> SIXTH_DIM
    assert names(block)[0] == ['c4', 'e4', 'g4', 'a4', 'c5']      # C6
    assert names(block)[1] == ['d4', 'f4', 'ab4', 'b4', 'd5']     # D dim7
    down = degrees('1 2 3 4 5') @ degrees('<1 -1 -3 -5>') >> SIXTH_DIM
    assert names(down)[0] == ['c4', 'a3', 'g3', 'e3']             # melody on top


def test_harmonize_example():
    def harmonize(melody):
        bebop = pitches('c4 d e f g ab a b c5')
        return (pitches(melody) << bebop) @ degrees('<1 -1 -3 -5 -7>') >> bebop
    h = harmonize('c d e g f ab g')
    assert names(h)[0] == ['c4', 'a3', 'g3', 'e3', 'c3']          # C6, melody on top
    assert names(h)[1] == ['d4', 'b3', 'ab3', 'f3', 'd3']         # D dim7
    assert len(h) == 7
    assert len(harmonize('c d') @ rhythm('4')) == 2


# ----------------------------------------------------------------- palette

def test_empty_palette_rejected():
    with pytest.raises(SyntaxError, match='Empty palette'):
        degrees('1') >> pitches('')


# -------------------------------------------------------------------- repr

SCOPE = {'Idea': Idea, 'pitches': pitches, 'degrees': degrees, 'rhythm': rhythm}


def roundtrips(idea):
    return eval(repr(idea), SCOPE) == idea


def test_repr_reads_like_the_expression_that_builds_it():
    assert repr(pitches('c d e')) == "degrees('1 2 3')"
    assert repr(degrees('1 2 3')) == "degrees('1 2 3')"
    assert repr(rhythm('4 r4 |: 8')) == "rhythm('4 r4 |: 8')"
    assert repr(pitches('c d') @ rhythm('4')) == "degrees('1 2') @ rhythm('4')"
    assert repr(degrees('<1 3 5> 2#') @ rhythm('2')) == "degrees('<1 3 5> 2#') @ rhythm('2')"
    assert repr(Idea()) == 'Idea()'


def test_repr_shows_the_loop_marker_that_plus_inserts():
    r = pitches('c d') @ rhythm('4 8') + pitches('e') @ rhythm('2 |: 16')
    assert repr(r) == "degrees('1 2 3') @ rhythm('4 8 2 |: 16')"


def test_repr_of_a_repeated_idea_stays_compact():
    r = pitches('c d') @ rhythm('4 8') * 2
    assert repr(r) == "degrees('1 2 1 2') @ rhythm('4 8')"


def test_repr_prefers_dotted_durations():
    assert repr(rhythm('4. 2.. 3/8 1/1 2/1')) == "rhythm('4. 2.. 4. 1 2/1')"


EXAMPLES = [
    Idea(),
    pitches('c d e'),
    pitches('<c4 e g> d <f a c5>'),
    pitches('c#4 db4 bb3 c##5 cbb2 c-1 b#-2'),
    pitches(''),
    degrees('1 2 3'),
    degrees('<1 3 5> -1 2# 3b 0 -7bb'),
    rhythm('4 8'),
    rhythm('4 r4 |: 8'),
    rhythm('|: 4 8'),
    rhythm('4. 2.. 3/8 12/8 2/1 1/12 5/8 7/16 3 r3 1/64 r1.'),
    pitches('c d e') @ rhythm('4 r4 |: 8'),
    degrees('1 2') @ rhythm('8'),
    rhythm('8') @ degrees('1 2 3') @ degrees('0 1 2 3'),
    (pitches('c d') @ rhythm('4 8')) + (pitches('e f g') @ rhythm('2 |: 16')),
    pitches('c d') + pitches('e') @ rhythm('r4 8'),
    pitches('c d e') @ rhythm('4 8') * 2,
    pitches('c d e') * 2 @ rhythm('4 8'),
    degrees('1 2') @ rhythm('4') + degrees('5') @ rhythm('2'),
    rhythm('4 8') + rhythm('2'),
    degrees('1 2 3 4 5') @ degrees('<1 3 5 7 9>') >> SIXTH_DIM,
    degrees('1 2 3 4 5') @ degrees('<1 -1 -3 -5>') @ rhythm('4') >> SIXTH_DIM,
]


@pytest.mark.parametrize('idea', EXAMPLES, ids=repr)
def test_repr_roundtrips_through_eval(idea):
    assert roundtrips(idea)


def test_harmonize_repr_roundtrips():
    bebop = pitches('c4 d e f g ab a b c5')
    h = (pitches('c d e g') << bebop) @ degrees('<1 -1 -3 -5 -7>') >> bebop
    assert len(h) == 4 and roundtrips(h)


@pytest.mark.parametrize('name', PALETTES)
def test_repr_roundtrips_every_pitch_the_palettes_make(name):
    p = PALETTES[name]
    for degree in range(-15, 25):
        for acc in (-2, -1, 0, 1, 2):
            single = Idea(Degrees([[p._at((degree, acc))]]))
            assert roundtrips(single), (name, degree, acc, repr(single))
    chord = Idea(Degrees([[p._at((d, a)) for d in (-3, 1, 4, 9)] for a in (-1, 0, 1)]))
    assert roundtrips(chord)


def test_repr_roundtrips_every_degree_form():
    for number in range(-20, 21):
        for acc in (-2, -1, 0, 1, 2):
            idea = Idea(Degrees([[(number, acc)], [(number, acc), (1, 0)]]))
            assert roundtrips(idea), (number, acc)


def test_repr_long_ideas_are_cut_short_and_say_so():
    long = degrees(' '.join(['29'] * 20))
    text = repr(long)
    assert text.count('29') == 16 and text.endswith("… +4')")
    assert len(repr(degrees(' '.join(['1'] * 500)))) < 120
    long_rhythm = repr(rhythm(' '.join(['8'] * 40)))
    assert long_rhythm.count('8') == 16 and '…' in long_rhythm
    exactly = degrees(' '.join(['29'] * 16))          # exactly at the limit: not cut
    assert '…' not in repr(exactly) and roundtrips(exactly)
    # a cut-short repr is for reading: it is not valid input
    with pytest.raises(SyntaxError):
        eval(text, SCOPE)
