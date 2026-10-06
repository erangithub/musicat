import re

from .errors import SyntaxError

LETTERS = 'cdefgab'
NATURAL_PITCH = (0, 2, 4, 5, 7, 9, 11)
ACCIDENTAL_OFFSET = {None: 0, 'bb': -2, 'b': -1, '#': 1, '##': 2}
ACCIDENTAL_NAME = {-2: 'bb', -1: 'b', 0: '', 1: '#', 2: '##'}


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
    groups = []
    position = 0
    for match in re.finditer(r'<([^<>]*)>|[^<>]+', text):
        if match.start() != position:
            raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
        position = match.end()
        if match.group(1) is None:
            groups.extend([Pitch(pitch)] for pitch in match.group().split())
        else:
            groups.append([Pitch(pitch) for pitch in match.group(1).split()])
    if position != len(text):
        raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
    return groups
