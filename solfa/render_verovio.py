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
        parts_events.append(part.idea._realize())
    actuals = []
    for events in parts_events:
        for _, _, nominal, tuplets in events:
            factor = Fraction(1)
            for k, j in (tuplets or ()):
                factor *= Fraction(j, k)
            actuals.append(nominal * factor)
    units = lcm(4, score.beat_type, *[d.denominator for d in actuals])
    divisions = units // 4
    bar_ticks = int(Fraction(score.beats, score.beat_type) * units)
    beat_ticks = units // score.beat_type
    group_ticks = beat_ticks * (3 if score.beats % 3 == 0 and score.beat_type >= 8 else 1)
    acc_map = {'': '', 'bb': 'flat-flat', 'b': 'flat', '#': 'sharp', '##': 'double-sharp',
               'n': 'natural'}

    parts = []
    for part, events in zip(score.parts, parts_events):
        measures = []
        notes = []
        filled = 0
        shown = set()                      # (letter, octave) altered earlier in this bar
        previous = ()                      # the tuplets of the event before this one
        for index, (_, group, nominal, tuplets) in enumerate(events):
            tuplets = tuplets or ()
            following = ((events[index + 1][3] or ())
                         if index + 1 < len(events) else ())
            opened = 0
            while (opened < len(previous) and opened < len(tuplets)
                   and previous[opened] == tuplets[opened]):
                opened += 1
            closed = 0
            while (closed < len(tuplets) and closed < len(following)
                   and tuplets[closed] == following[closed]):
                closed += 1
            begin = [f'<tuplet type="start" number="{d + 1}"/>'
                     for d in range(opened, len(tuplets))]
            end = [f'<tuplet type="stop" number="{d + 1}"/>'
                   for d in range(closed, len(tuplets))]
            previous = tuplets
            factor = Fraction(1)
            for k, j in tuplets:
                factor *= Fraction(j, k)
            tuplet_xml = ''
            if tuplets:
                k, j = tuplets[-1]
                tuplet_xml = (f'<time-modification><actual-notes>{k}</actual-notes>'
                              f'<normal-notes>{j}</normal-notes></time-modification>')
            # a note that would cross a barline is split at the bar and tied
            # to its continuation, so every bar fills exactly
            remaining = int(nominal * factor * units)
            carried = False                     # a tie arriving from the last bar
            first = True
            while remaining > 0:
                ticks = min(remaining, bar_ticks - filled)
                name, dots, _, _ = _duration_type(Fraction(ticks, units) / factor)
                dots_xml = '<dot/>' * dots
                start = ticks < remaining
                if group:
                    tie_xml = ('<tie type="stop"/>' if carried else '') \
                        + ('<tie type="start"/>' if start else '')
                    tied = ('continue' if carried and start else
                            'stop' if carried else 'start' if start else None)
                else:
                    tie_xml, tied = '', None
                notations = []
                if tied:
                    notations.append(f'<tied type="{tied}"/>')
                if first:
                    notations.extend(begin)
                if not start:
                    notations.extend(end)
                if not group:
                    body = (f'<note><rest/><duration>{ticks}</duration>{tie_xml}'
                            f'<voice>1</voice>'
                            f'<type>{name}</type>{dots_xml}{tuplet_xml}</note>')
                else:
                    body = ''
                    for i, (number, alter) in enumerate(group):
                        alter = alter or 0
                        letter = LETTERS[(number - 1) % 7].upper()
                        octave = (number - 1) // 7 + ORIGIN // 7
                        slot = (letter, octave)
                        run = '#' * alter if alter > 0 else 'b' * -alter
                        if alter:
                            shown.add(slot)
                        elif slot in shown:
                            shown.discard(slot)    # this natural cancels an earlier accidental
                            run = 'n'
                        symbol = acc_map[run]
                        acc = f'<accidental>{symbol}</accidental>' if symbol else ''
                        alt = f'<alter>{alter}</alter>' if alter else ''
                        body += ('<note><chord/>' if i else '<note>') + (
                            f'<pitch><step>{letter}</step>{alt}'
                            f'<octave>{octave}</octave></pitch>'
                            f'<duration>{ticks}</duration>{tie_xml}<voice>1</voice>'
                            f'<type>{name}</type>{dots_xml}{acc}{tuplet_xml}</note>')
                notes.append((body, ticks, None if not group else name, notations))
                filled += ticks
                remaining -= ticks
                carried = start
                first = False
                if filled >= bar_ticks:
                    beams = _beams([(t, kind) for _, t, kind, _ in notes],
                                   beat_ticks, group_ticks)
                    measures.append(''.join(
                        (note.replace('</note>', beam + '</note>', 1) if beam else note)
                        .replace('</note>',
                                 (f'<notations>{"".join(n)}</notations>' if n else '')
                                 + '</note>', 1)
                        for (note, _, _, n), beam in zip(notes, beams)))
                    notes = []
                    filled = 0
                    shown = set()               # a new bar starts fresh
        if notes:
            beams = _beams([(t, kind) for _, t, kind, _ in notes], beat_ticks, group_ticks)
            measures.append(''.join(
                (note.replace('</note>', beam + '</note>', 1) if beam else note)
                .replace('</note>',
                         (f'<notations>{"".join(n)}</notations>' if n else '')
                         + '</note>', 1)
                for (note, _, _, n), beam in zip(notes, beams)))

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
