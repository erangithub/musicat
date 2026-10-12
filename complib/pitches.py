from __future__ import annotations
import re
from .errors import SyntaxError

LETTERS = 'cdefgab'
NATURAL_PITCH = (0, 2, 4, 5, 7, 9, 11)

class Pitch:
    def __init__(self, name: str = "", min_octave: int = 0):
        if not name:
            self.idx = 0
            self.acc = 0
        else:
            match = re.fullmatch('([a-gA-G])(b*|#*)?(-?[0-9]+)?', name)
            if not match:
                raise SyntaxError(f'Illegal pitch name "{name}"')
            self.idx = LETTERS.index(match.group(1).lower())
            accidental_name = match.group(2)
            if not accidental_name:
                self.acc = 0
            elif accidental_name[0] == '#':
                self.acc = len(accidental_name)
            else:
                self.acc = -len(accidental_name)
            octave = int(match.group(3)) if match.group(3) else min_octave
            self.idx += octave * 7

    def midipitch(self):
        return NATURAL_PITCH[self.idx % 7] + 12 * ((self.octave())+1) + self.acc

    def _normpitch(self):
        return self.midipitch() - 12

    def octave(self):
        return self.idx // 7

    def root(self):
        return LETTERS[self.idx % 7]

    def accidental(self):
        if self.acc > 0:
            return "#" * self.acc 
        if self.acc < 0:
            return "b" * -self.acc
        return "" 

    def __eq__(self, other: Pitch):
        if not isinstance(other, Pitch):
            return NotImplemented
        return (self.idx, self.acc) == (other.idx, other.acc)

    def __hash__(self):
        return hash((self.idx, self.acc))

    def __str__(self):
        return f'{self.root()}{self.accidental()}{self.octave()}'
    def __repr__(self):
        return f"Pitch('{self.__str__()}')"

    def __add__(self, other: Pitch):
        result = Pitch()
        result.idx = self.idx + other.idx
        result.acc = self._normpitch() + other._normpitch() - result._normpitch()
        return result

    def __sub__(self, other):
        return self + (-other)

    def __neg__(self):
        result = Pitch()
        result.idx = -self.idx
        result.acc = -self._normpitch() - result._normpitch()
        return result

def parse_pitches(text):
    groups = []
    min_octave = 4
    position = 0
    for match in re.finditer(r'<([^<>]*)>|[^<>]+', text):
        if match.start() != position:
            raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
        position = match.end()
        if match.group(1) is None:
            for name in match.group().split():
                pitch = Pitch(name, min_octave)
                explicit = re.search(r'-?[0-9]+$', name)
                if explicit:
                    min_octave = int(explicit.group())
                groups.append([pitch])
        else:
            names = match.group(1).split()
            if not names:
                groups.append([])
                continue
            root = Pitch(names[0], min_octave)
            chord = [root]
            running = root.midipitch()
            for name in names[1:]:
                pitch = Pitch(name, min_octave)
                if not re.search(r'-?[0-9]+$', name):
                    while pitch.midipitch() <= running:
                        pitch = Pitch(f'{pitch.root()}{pitch.accidental()}{pitch.octave() + 1}')
                chord.append(pitch)
                running = pitch.midipitch()
            if chord == []:
                raise SyntaxError(f'Empty chord near "{text[position:].strip()}"')
            groups.append(chord)
            min_octave = root.octave()
    if position != len(text):
        raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
    return groups
