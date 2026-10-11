from fractions import Fraction
from math import lcm

from .errors import SyntaxError
from .rhythm import EIGHTH, HALF, QUARTER, SIXTEENTH, THIRTY_SECOND, WHOLE
from .score import Part, Score


def show(musicxml=None):
    import verovio
    if musicxml is None:
        with open('mock/probe.musicxml') as f:
            musicxml = f.read()
    toolkit = verovio.toolkit()
    toolkit.setOptions({'adjustPageHeight': True, 'scale': 40})
    if not toolkit.loadData(musicxml):
        raise SyntaxError('Illegal MusicXML')
    svg = toolkit.renderToSVG(1)
    try:
        from IPython.display import SVG, display
        display(SVG(svg))
    except ImportError:
        pass


def _duration_type(duration):
    types = (('whole', WHOLE), ('half', HALF), ('quarter', QUARTER),
             ('eighth', EIGHTH), ('16th', SIXTEENTH), ('32nd', THIRTY_SECOND),
             ('64th', Fraction(1, 64)), ('128th', Fraction(1, 128)))
    if not duration:
        return 'quarter', 0, None, None
    candidates = []
    for name, base in types:
        for dots in range(3):
            plain = base * (2 - Fraction(1, 2 ** dots))
            if duration == plain:
                return name, dots, None, None
            ratio = plain / duration
            if 2 <= ratio.numerator <= 9 and ratio.numerator > ratio.denominator \
                    and ratio.denominator in (1, 2, 4):
                actual, normal = ratio.numerator, ratio.denominator
                candidates.append((abs(float(ratio) - 1), name, dots, actual, normal))
    if candidates:
        _, name, dots, actual, normal = min(candidates)
        return name, dots, actual, normal
    nearest = min((abs(float(base - duration)), name) for name, base in types)[1]
    return nearest, 0, None, None


def _beams(measure, beat_ticks, group_ticks):
    """Beam XML for each note of one measure, in order. `measure` is a list of
    (duration_ticks, note_type) pairs, note_type None for rests; returns one
    string per note to insert before its closing </note> tag."""
    ranks = {'eighth': 1, '16th': 2, '32nd': 3, '64th': 4, '128th': 5}
    items = []
    start = 0
    for ticks, name in measure:
        items.append([start, ranks.get(name, 0)])
        start += ticks
    xml = [''] * len(items)
    for level in range(1, max((rank for _, rank in items), default=0) + 1):
        slot = group_ticks if level == 1 else beat_ticks // 2 ** (level - 2)
        i = 0
        while i < len(items):
            if items[i][1] < level:
                i += 1
                continue
            j = i
            while j < len(items) and items[j][1] >= level \
                    and items[j][0] // slot == items[i][0] // slot:
                j += 1
            if j - i > 1:
                for k in range(i, j):
                    kind = 'begin' if k == i else 'end' if k == j - 1 else 'continue'
                    xml[k] += f'<beam number="{level}">{kind}</beam>'
                i = j
            else:
                i += 1
    return xml


def show_score(score: Score):
    parts_events = []
    for part in score.parts:
        idea = part.idea
        if (idea.pitches is None and idea.rhythm is None):
            raise(RuntimeError("Can't display degree based idea"))
        parts_events.append(idea.events())
    units = lcm(4, score.beat_type,
                *[duration.denominator for events in parts_events
                  for _, duration in events])
    divisions = units // 4
    bar_ticks = int(Fraction(score.beats, score.beat_type) * units)
    beat_ticks = units // score.beat_type
    group_ticks = beat_ticks * (3 if score.beats % 3 == 0 and score.beat_type >= 8 else 1)
    acc_map = {'': '', 'bb': 'flat-flat', 'b': 'flat', '#': 'sharp', '##': 'double-sharp'}

    parts = []
    for part, events in zip(score.parts, parts_events):
        measures = []
        notes = []
        filled = 0
        for group, duration in events:
            name, dots, actual, normal = _duration_type(duration)
            dots_xml = '<dot/>' * dots
            tuplet_xml = (f'<time-modification><actual-notes>{actual}</actual-notes>'
                          f'<normal-notes>{normal}</normal-notes></time-modification>'
                          if actual else '')
            ticks = int(duration * units)
            if not group:
                body = (f'<note><rest/><duration>{ticks}</duration><voice>1</voice>'
                        f'<type>{name}</type>{dots_xml}{tuplet_xml}</note>')
            else:
                body = ''
                for i, pitch in enumerate(group):
                    symbol = acc_map[pitch.accidental()]
                    alter = pitch.acc
                    acc = f'<accidental>{symbol}</accidental>' if symbol else ''
                    alt = f'<alter>{alter}</alter>' if alter else ''
                    octave = pitch.octave()
                    body += ('<note><chord/>' if i else '<note>') + (
                        f'<pitch><step>{pitch.root().upper()}</step>{alt}'
                        f'<octave>{octave}</octave></pitch>'
                        f'<duration>{ticks}</duration><voice>1</voice>'
                        f'<type>{name}</type>{dots_xml}{acc}{tuplet_xml}</note>')
            if notes and filled + ticks > bar_ticks:
                beams = _beams([(t, kind) for _, t, kind in notes], beat_ticks, group_ticks)
                measures.append(''.join(
                    note.replace('</note>', beam + '</note>', 1) if beam else note
                    for (note, _, _), beam in zip(notes, beams)))
                notes = []
                filled = 0
            notes.append((body, ticks, None if not group else name))
            filled += ticks
        if notes:
            beams = _beams([(t, kind) for _, t, kind in notes], beat_ticks, group_ticks)
            measures.append(''.join(
                note.replace('</note>', beam + '</note>', 1) if beam else note
                for (note, _, _), beam in zip(notes, beams)))

        attributes = (f'<attributes><divisions>{divisions}</divisions>'
                      '<key><fifths>0</fifths></key>'
                      f'<time><beats>{score.beats}</beats>'
                      f'<beat-type>{score.beat_type}</beat-type></time>'
                      '<clef><sign>G</sign><line>2</line></clef></attributes>')
        body = ''.join(f'<measure number="{i}">{attributes if i == 1 else ""}{m}</measure>'
                       for i, m in enumerate(measures, 1))
        parts.append(f'<part id="P{len(parts) + 1}">{body}</part>')

    part_list = ''.join(f'<score-part id="P{i}"><part-name>{part.name}</part-name>'
                        f'</score-part>'
                        for i, part in enumerate(score.parts, 1))
    show('<?xml version="1.0" encoding="UTF-8"?>'
         '<score-partwise version="4.0"><part-list>'
         f'{part_list}</part-list>'
         f'{"".join(parts)}</score-partwise>')
