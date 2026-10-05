import re
from fractions import Fraction
from math import lcm

LETTERS = 'cdefgab'
NATURAL_PITCH = (0, 2, 4, 5, 7, 9, 11)
ACCIDENTAL_OFFSET = {None: 0, 'bb': -2, 'b': -1, '#': 1, '##': 2}
ACCIDENTAL_NAME = {-2: 'bb', -1: 'b', 0: '', 1: '#', 2: '##'}

WHOLE = Fraction(1)
HALF = Fraction(1, 2)
QUARTER = Fraction(1, 4)
EIGHTH = Fraction(1, 8)
SIXTEENTH = Fraction(1, 16)
THIRTY_SECOND = Fraction(1, 32)
DOT = Fraction(3, 2)
DOUBLE_DOT = Fraction(7, 4)

class SyntaxError(Exception):
    pass

class Pitch:
    def __init__(self, name: str):
        match = re.fullmatch('([a-gA-G])(bb|b|#|##)?(-1|[0-7])?', name)
        if not match:
            raise SyntaxError(f'Illegal pitch name "{name}"')
        self.name = name
        self.root = match.group(1)
        self.accidental = match.group(2)
        self.octave = int(match.group(3)) if match.group(3) else None

    def midipitch(self):
        idx = LETTERS.index(self.root.lower())
        base = NATURAL_PITCH[idx]
        if self.octave is not None:
            base += 12 * (self.octave+1)
        base += ACCIDENTAL_OFFSET[self.accidental]

        return base

    def __eq__(self, other):
        if not isinstance(other, Pitch):
            return NotImplemented
        return (self.root.lower(), self.accidental, self.octave) == \
               (other.root.lower(), other.accidental, other.octave)

    def __hash__(self):
        return hash((self.root.lower(), self.accidental, self.octave))

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Pitch('{self.name}')"


class Event:
    def __init__(self, pitches=None, duration=QUARTER):
        parsed = []
        for pitch in (pitches or []):
            if isinstance(pitch, str):
                pitch = Pitch(pitch)
            elif not isinstance(pitch, Pitch):
                raise SyntaxError(f'Illegal pitch {pitch!r}')
            parsed.append(pitch)
        self.pitches = parsed
        self.duration = duration

    def midipitches(self):
        return [p.midipitch() for p in self.pitches]

    def __eq__(self, other):
        if not isinstance(other, Event):
            return NotImplemented
        return (type(self) is type(other) and self.pitches == other.pitches
                and self.duration == other.duration)

    def __hash__(self):
        return hash((type(self), tuple(self.pitches), self.duration))

    def __str__(self):
        body = ' '.join(str(p) for p in self.pitches)
        return f'{body} {self.duration}' if body else str(self.duration)

    def __repr__(self):
        body = ' '.join(str(p) for p in self.pitches)
        pitches = f"'{body}', " if body else ''
        return f"{type(self).__name__}({pitches}{self.duration})"


class Note(Event):
    def __init__(self, pitch, duration=QUARTER):
        super().__init__([pitch], duration)


class Chord(Event):
    pass


class Rest(Event):
    def __init__(self, duration=QUARTER):
        super().__init__(None, duration)

    def __str__(self):
        return f'r {self.duration}'


Sequence = list[Event]
Duration = Fraction
Rhythm = list[Duration]


def major_scale(root: str):
    root_pitch = Pitch(root)

    start = LETTERS.index(root_pitch.root.lower())
    root_pc = (NATURAL_PITCH[start] + ACCIDENTAL_OFFSET[root_pitch.accidental]) % 12

    pitches = []
    for degree in range(7):
        idx = (start + degree) % 7
        letter = LETTERS[idx]
        pitch_pc = (root_pc + NATURAL_PITCH[degree]) % 12
        delta = (pitch_pc - NATURAL_PITCH[idx]) % 12
        if delta > 6:
            delta -= 12
        pitches.append(Pitch(letter + ACCIDENTAL_NAME[delta]))
    return pitches 

def to_pitches(text):
    tokens = text.split()
    return list(map(Pitch, tokens))


def to_rhythm(text):
    tokens = text.split()
    durations = []
    for token in tokens:
        match = re.fullmatch(r'(\d*)(?:/(\d+))?(\.*)', token)
        if not match:
            raise SyntaxError(f'Illegal duration "{token}"')
        numerator, denominator, dots = match.group(1), match.group(2), match.group(3)
        if not numerator and denominator is None:
            raise SyntaxError(f'Illegal duration "{token}"')
        if denominator is None:
            duration = Fraction(int(numerator))
        else:
            denominator = int(denominator)
            if not denominator:
                raise SyntaxError(f'Illegal duration "{token}"')
            duration = Fraction(int(numerator or 1), denominator)
        durations.append(duration * (2 - Fraction(1, 2 ** len(dots))))
    return durations


def combine(pitches, rhythm):
    if not rhythm:
        raise SyntaxError('Empty rhythm')
    events = []
    for i, group in enumerate(pitches):
        group = group if isinstance(group, (list, tuple)) else [group]
        duration = rhythm[i % len(rhythm)]
        if not group:
            events.append(Rest(duration))
        elif len(group) == 1:
            events.append(Note(group[0], duration))
        else:
            events.append(Chord(group, duration))
    return events


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


def show_seq(sequence: Sequence):
    if not sequence:
        raise SyntaxError('Empty sequence')
    units = lcm(4, *[event.duration.denominator for event in sequence])
    divisions = units // 4
    accidental = {None: ('', 0), 'bb': ('flat-flat', -2), 'b': ('flat', -1),
                  '#': ('sharp', 1), '##': ('double-sharp', 2)}

    measures = []
    notes = []
    filled = 0
    for event in sequence:
        name, dots, actual, normal = _duration_type(event.duration)
        dots_xml = '<dot/>' * dots
        tuplet_xml = (f'<time-modification><actual-notes>{actual}</actual-notes>'
                      f'<normal-notes>{normal}</normal-notes></time-modification>'
                      if actual else '')
        ticks = int(event.duration * units)
        if isinstance(event, Rest):
            body = (f'<note><rest/><duration>{ticks}</duration><voice>1</voice>'
                    f'<type>{name}</type>{dots_xml}{tuplet_xml}</note>')
        elif isinstance(event, (Note, Chord)):
            body = ''
            for i, pitch in enumerate(event.pitches):
                symbol, alter = accidental[pitch.accidental]
                acc = f'<accidental>{symbol}</accidental>' if symbol else ''
                alt = f'<alter>{alter}</alter>' if alter else ''
                octave = 4 if pitch.octave is None else pitch.octave
                body += ('<note><chord/>' if i else '<note>') + (
                    f'<pitch><step>{pitch.root.upper()}</step>{alt}'
                    f'<octave>{octave}</octave></pitch>'
                    f'<duration>{ticks}</duration><voice>1</voice>'
                    f'<type>{name}</type>{dots_xml}{acc}{tuplet_xml}</note>')
        else:
            raise SyntaxError(f'Illegal event {type(event).__name__}')
        if notes and filled + ticks > units:
            measures.append(''.join(notes))
            notes = []
            filled = 0
        notes.append(body)
        filled += ticks
    if notes:
        measures.append(''.join(notes))

    attributes = (f'<attributes><divisions>{divisions}</divisions>'
                  '<key><fifths>0</fifths></key>'
                  '<time><beats>4</beats><beat-type>4</beat-type></time>'
                  '<clef><sign>G</sign><line>2</line></clef></attributes>')
    body = ''.join(f'<measure number="{i}">{attributes if i == 1 else ""}{m}</measure>'
                   for i, m in enumerate(measures, 1))
    show('<?xml version="1.0" encoding="UTF-8"?>'
         '<score-partwise version="4.0"><part-list>'
         '<score-part id="P1"><part-name>Music</part-name></score-part></part-list>'
         f'<part id="P1">{body}</part></score-partwise>')

if __name__ == "__main__":
    print('Welcome to complib')
    print(major_scale('d'))

