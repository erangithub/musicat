"""Check bars 1-8 of examples/k545.py against two independent encodings.

* music21's bundled corpus (needs `pip install music21`, nothing else).
* The Neue Mozart-Ausgabe kern file from github.com/craigsapp/mozart-piano-sonatas
  (kern/sonata15-1.krn). Download it and point K545_KERN at it to run that test.
  Check that dataset's license before committing the file to your own repo.
"""
import os
from fractions import Fraction as F

import pytest

from complib import k545
from complib.degrees import white_keys

BARS = 8


def ours(idea):
    """[(offset in quarters, sorted midi numbers, length in quarters)] per event."""
    out, offset = [], F(0)
    for group, duration in idea.events():
        # a degree's sound, with middle C at 60 like the reference encodings
        sounds = (white_keys._at((n, 0))[0] + a + 60 for n, a in group)
        out.append((offset, tuple(sorted(sounds)), duration * 4))
        offset += duration * 4
    return out


def theirs(part, bars=BARS):
    out = []
    for el in part.flatten().notesAndRests:
        if el.offset >= bars * 4:
            continue
        midis = () if el.isRest else tuple(sorted(p.midi for p in el.pitches))
        out.append((F(el.offset).limit_denominator(64), midis,
                    F(el.quarterLength).limit_denominator(64)))
    return out


def differences(idea, part):
    a, b = ours(idea), theirs(part)
    assert len(a) == len(b), f'{len(a)} events here, {len(b)} in the reference'
    return [(x, y) for x, y in zip(a, b) if x != y]


def test_both_hands_are_eight_bars_long():
    for idea in (k545.right_hand, k545.left_hand):
        events = ours(idea)
        assert events[-1][0] + events[-1][2] == BARS * 4


def test_score_builds_with_two_parts():
    score = k545.score()
    assert [str(part) for part in score.parts] == ['Right hand', 'Left hand']


def test_matches_the_music21_corpus():
    converter = pytest.importorskip('music21.corpus')
    score = converter.parse('mozart/k545/movement1_exposition.mxl')
    assert differences(k545.right_hand, score.parts[0]) == []
    # One chord differs. Bar 7, beat 1 of the left hand is D3+C4 here and in the
    # NMA edition (a D minor seventh under the F of the right hand), but the corpus
    # encoding has D3+B3, which would repeat the chord of beat 4.
    d3, c4, b3 = 50, 60, 59
    assert differences(k545.left_hand, score.parts[1]) == [
        ((F(24), (d3, c4), F(1)), (F(24), (d3, b3), F(1)))]


@pytest.mark.skipif('K545_KERN' not in os.environ,
                    reason='set K545_KERN to the path of sonata15-1.krn')
def test_matches_the_nma_edition():
    music21 = pytest.importorskip('music21')
    score = music21.converter.parse(os.environ['K545_KERN'], format='humdrum')
    assert differences(k545.right_hand, score.parts[0]) == []
    assert differences(k545.left_hand, score.parts[1]) == []
