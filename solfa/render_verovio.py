from fractions import Fraction
from math import lcm

from .errors import SyntaxError
from .pitches import LETTERS, ORIGIN
from .rhythm import EIGHTH, HALF, QUARTER, SIXTEENTH, THIRTY_SECOND, WHOLE
from .score import Part, Score


def show(musicxml=None):
    import verovio
    if musicxml is None:
        with open('solfa/mock/probe.musicxml') as f:
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
        parts_events.append(part.idea.events())
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
            # a note that would cross a barline is split at the bar and tied
            # to its continuation, so every bar fills exactly
            remaining = int(duration * units)
            carried = False                     # a tie arriving from the last bar
            while remaining > 0:
                ticks = min(remaining, bar_ticks - filled)
                name, dots, actual, normal = _duration_type(Fraction(ticks, units))
                dots_xml = '<dot/>' * dots
                tuplet_xml = (f'<time-modification><actual-notes>{actual}</actual-notes>'
                              f'<normal-notes>{normal}</normal-notes></time-modification>'
                              if actual else '')
                start = ticks < remaining
                if group:
                    tie_xml = ('<tie type="stop"/>' if carried else '') \
                        + ('<tie type="start"/>' if start else '')
                    tied = ('continue' if carried and start else
                            'stop' if carried else 'start' if start else None)
                else:
                    tie_xml, tied = '', None
                if not group:
                    body = (f'<note><rest/><duration>{ticks}</duration>{tie_xml}'
                            f'<voice>1</voice>'
                            f'<type>{name}</type>{dots_xml}{tuplet_xml}</note>')
                else:
                    body = ''
                    for i, (number, alter) in enumerate(group):
                        alter = alter or 0
                        run = '#' * alter if alter > 0 else 'b' * -alter
                        symbol = acc_map[run]
                        acc = f'<accidental>{symbol}</accidental>' if symbol else ''
                        alt = f'<alter>{alter}</alter>' if alter else ''
                        body += ('<note><chord/>' if i else '<note>') + (
                            f'<pitch><step>{LETTERS[(number - 1) % 7].upper()}</step>{alt}'
                            f'<octave>{(number - 1) // 7 + ORIGIN // 7}</octave></pitch>'
                            f'<duration>{ticks}</duration>{tie_xml}<voice>1</voice>'
                            f'<type>{name}</type>{dots_xml}{acc}{tuplet_xml}</note>')
                notes.append((body, ticks, None if not group else name, tied))
                filled += ticks
                remaining -= ticks
                carried = start
                if filled >= bar_ticks:
                    beams = _beams([(t, kind) for _, t, kind, _ in notes],
                                   beat_ticks, group_ticks)
                    measures.append(''.join(
                        (note.replace('</note>', beam + '</note>', 1) if beam else note)
                        .replace('</note>',
                                 (f'<notations><tied type="{k}"/></notations>' if k else '')
                                 + '</note>')
                        for (note, _, _, k), beam in zip(notes, beams)))
                    notes = []
                    filled = 0
        if notes:
            beams = _beams([(t, kind) for _, t, kind, _ in notes], beat_ticks, group_ticks)
            measures.append(''.join(
                (note.replace('</note>', beam + '</note>', 1) if beam else note)
                .replace('</note>',
                         (f'<notations><tied type="{k}"/></notations>' if k else '')
                         + '</note>')
                for (note, _, _, k), beam in zip(notes, beams)))

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
