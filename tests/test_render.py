import re

import pytest
import verovio

from complib import Part, Score, SyntaxError, show, show_score, pitches, rhythm

def test_xml_envelope(capture):
    (pitches('c') + rhythm('/4')).show()
    xml = capture[0]
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert '<score-partwise version="4.0">' in xml
    assert xml.endswith('</score-partwise>')
    assert '<measure number="1">' in xml


@pytest.mark.parametrize('time,r,expected', [
    ('4/4', '/4', 1),
    ('4/4', '/8', 2),
    ('4/4', '/16', 4),
    ('4/4', '1/12', 3),
    ('4/4', '1/96', 24),
    ('6/8', '/4', 2),
])
def test_divisions(capture, time, r, expected):
    (pitches('c') + rhythm(r)).show(time)
    assert f'<divisions>{expected}</divisions>' in capture[0]


def test_attributes_only_in_first_measure(capture):
    Part(pitches('c d e f') + (rhythm('/4'))).show()
    xml = capture[0]
    assert xml.count('<divisions>') == 1
    assert xml.count('<key>') == 1
    assert xml.count('<time>') == 1
    assert xml.count('<clef>') == 1


def test_time_signature_in_xml(capture):
    Part(pitches('c') + (rhythm('/8'))).show('6/8')
    assert '<beats>6</beats><beat-type>8</beat-type>' in capture[0]


def test_part_list_and_ids(capture):
    Score([Part(pitches('c') + (rhythm('/4')), 'Flute'), Part(pitches('d') + (rhythm('/4')), 'Oboe')], '3/4').show()
    xml = capture[0]
    assert '<part-name>Flute</part-name>' in xml
    assert '<part-name>Oboe</part-name>' in xml
    assert '<part id="P1">' in xml
    assert '<part id="P2">' in xml


def test_parts_share_divisions(capture):
    show_score(Score([
        Part(pitches('c d') + (rhythm('/4')), 'A'),
        Part(pitches('e f') + (rhythm('/16')), 'B'),
    ]))
    xml = capture[0]
    assert xml.count('<divisions>') == 2
    assert xml.count('<divisions>4</divisions>') == 2


def test_alignment_with_explicit_rests(capture):
    show_score(Score([
        Part(pitches('c d e f') + (rhythm('/4')), 'A'),
        Part(pitches('<> g a b') + (rhythm('/4')), 'B'),
    ]))
    xml = capture[0]
    assert xml.count('<rest/>') == 1
    measures = re.findall(r'<measure number="\d+">(.*?)</measure>', xml)
    totals = [sum(int(d) for d in re.findall(r'<duration>(\d+)</duration>', m))
              for m in measures]
    assert totals == [4, 4]


@pytest.mark.parametrize('time,text,r,expected', [
    ('4/4', 'c d e f g a b c', '/4', [4, 4]),
    ('3/4', 'c d e f g a b c', '/4', [3, 3, 2]),
    ('6/8', 'c d e f g a b c', '/4', [3, 3, 2]),
    ('2/2', 'c d e f g a b c', '/4', [4, 4]),
    ('5/4', 'c d e f g a b c', '/4', [5, 3]),
    ('3/8', 'c d e f g a b c', '/8', [3, 3, 2]),
])
def test_events_per_bar(capture, time, text, r, expected):
    (pitches(text) + rhythm(r)).show(time)
    measures = re.findall(r'<measure number="\d+">(.*?)</measure>', capture[0])
    assert [m.count('<pitch>') for m in measures] == expected


@pytest.mark.parametrize('time,text,r,expected_bars', [
    ('4/4', 'c d', '/4', 1),
    ('4/4', 'c', '1', 1),
    ('3/8', 'c', '1', 1),
    ('4/4', 'c d e f g a b c', '/4', 2),
    ('5/4', 'c d e f g a b c', '/4', 2),
    ('3/8', 'c d e f', '/8', 2),
])
def test_bar_count(capture, time, text, r, expected_bars):
    (pitches(text) + (rhythm(r))).show(time)
    measures = re.findall(r'<measure number="\d+">', capture[0])
    assert len(measures) == expected_bars


def test_note_types_and_dots(capture):
    (pitches('c d') + (rhythm('/4 1/8.'))).show()
    xml = capture[0]
    assert '<type>quarter</type>' in xml
    assert '<type>eighth</type><dot/>' in xml


def test_duration_ticks_match_divisions(capture):
    (pitches('c d') + (rhythm('/4 /8'))).show()
    durations = re.findall(r'<duration>(\d+)</duration>', capture[0])
    assert durations == ['2', '1']


def test_tuplet_time_modification(capture):
    (pitches('c d e') + (rhythm('1/12'))).show()
    xml = capture[0]
    assert ('<time-modification><actual-notes>3</actual-notes>'
            '<normal-notes>2</normal-notes></time-modification>') in xml


def test_accidentals(capture):
    (pitches('f# bb e') + (rhythm('/4'))).show()
    xml = capture[0]
    assert '<step>F</step><alter>1</alter>' in xml
    assert '<accidental>sharp</accidental>' in xml
    assert '<step>B</step><alter>-1</alter>' in xml
    assert '<accidental>flat</accidental>' in xml
    assert '<step>E</step><octave>0</octave>' in xml
    assert xml.count('<accidental>') == 2


def test_octave_defaults_to_zero(capture):
    (pitches('c c3') + (rhythm('/4'))).show()
    xml = capture[0]
    assert '<step>C</step><octave>0</octave>' in xml
    assert '<step>C</step><octave>3</octave>' in xml


@pytest.mark.parametrize('time,r,text,expected', [
    ('4/4', '/8', 'c d e f g a b c', 8),
    ('4/4', '/16', 'c d e f g a b c', 16),
    ('6/8', '/8', 'c d e f g a b c', 8),
    ('6/8', '/16', 'c d e f g a b c', 16),
    ('2/2', '/8', 'c d e f g a b c d e f g a b c d', 16),
    ('4/4', '/8', '<c e g> <d f a> <e g b> <f a c>', 4),
    ('4/4', '1/12 1/12 1/12', 'c d e f g a', 6),
    ('4/4', '/4', 'c d e f', 0),
    ('4/4', '/8 /4 /4 /4 /4', 'c d e f g', 0),
    ('3/8', '/8', 'c d e f', 3),
    ('5/4', '/8', 'c d e f g a b c d e', 10),
    ('4/4', '1/16 /16 /16 /16', 'c <> e f g', 4),
    ('5/8', '/8', 'c d e f g', 0),
    ('7/8', '/8', 'c d e f g a b', 0),
])
def test_beam_counts(capture, time, r, text, expected):
    (pitches(text) + rhythm(r)).show(time)
    assert capture[0].count('<beam ') == expected


def test_beam_kinds_paired(capture):
    Part(pitches('c d e f g a b c') + (rhythm('/8'))).show()
    kinds = re.findall(r'<beam number="1">(begin|end|continue)</beam>', capture[0])
    assert kinds == ['begin', 'end'] * 4


def test_beam_levels_for_sixteenths(capture):
    Part(pitches('c d e f g a b c') + (rhythm('/16'))).show()
    xml = capture[0]
    assert re.findall(r'<beam number="1">(\w+)</beam>', xml) == (
        ['begin', 'continue', 'continue', 'end'] * 2)
    assert re.findall(r'<beam number="2">(\w+)</beam>', xml) == (
        ['begin', 'continue', 'continue', 'end'] * 2)


def test_beam_breaks_at_rest(capture):
    Part(pitches('c d e <> f') + (rhythm('/16'))).show()
    xml = capture[0]
    kinds = re.findall(r'<beam number="1">(begin|continue|end)</beam>', xml)
    assert kinds == ['begin', 'continue', 'end']
    assert re.findall(r'<beam number="2">(begin|continue|end)</beam>', xml) == kinds


def test_beams_do_not_cross_barlines(capture):
    Part(pitches('c d e f g a') + (rhythm('/8'))).show('3/8')
    measures = re.findall(r'<measure number="\d+">(.*?)</measure>', capture[0])
    assert [m.count('<beam ') for m in measures] == [3, 3]


def test_beam_on_primary_chord_note_only(capture):
    Part(pitches('<c e g> <d f a> <e g b> <f a c>') + (rhythm('/8'))).show()
    notes = re.findall(r'<note>.*?</note>', capture[0])
    chord_notes = [note for note in notes if '<chord/>' in note]
    assert len(chord_notes) == 8
    assert not any('<beam' in note for note in chord_notes)
    assert sum('<beam' in note for note in notes) == 4


def test_verovio_loads_output(capture):
    show_score(Score([
        Part(pitches('<c e g> <d f a> f# bb') + (rhythm('1/12 /8 1/8.')),
             'Flute'),
        Part(pitches('c <> e f') + (rhythm('/16')), 'Oboe'),
    ], '6/8'))
    toolkit = verovio.toolkit()
    assert toolkit.loadData(capture[0])


def test_show_rejects_illegal_musicxml():
    with pytest.raises(SyntaxError):
        show('<not musicxml/>')


def test_show_default_sample_loads():
    show()
