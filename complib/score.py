import re

from .errors import SyntaxError
from .events import Event


class Part:
    def __init__(self, sequence, name='Music'):
        if not sequence:
            raise SyntaxError('Empty part')
        for event in sequence:
            if not isinstance(event, Event):
                raise SyntaxError(f'Illegal event {event!r}')
        self.sequence = sequence
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Part('{self.name}', {len(self.sequence)} events)"


class Score:
    def __init__(self, parts, time='4/4'):
        if not parts:
            raise SyntaxError('Empty score')
        for part in parts:
            if not isinstance(part, Part):
                raise SyntaxError(f'Illegal part {part!r}')
        match = re.fullmatch(r'(\d+)/(\d+)', time)
        if not match:
            raise SyntaxError(f'Illegal time signature "{time}"')
        beats, beat_type = int(match.group(1)), int(match.group(2))
        if not beats or beat_type not in (1, 2, 4, 8, 16, 32, 64):
            raise SyntaxError(f'Illegal time signature "{time}"')
        self.parts = parts
        self.time = time
        self.beats = beats
        self.beat_type = beat_type

    def __str__(self):
        return f'{", ".join(str(part) for part in self.parts)} in {self.time}'

    def __repr__(self):
        return f'Score({", ".join(repr(part) for part in self.parts)}, {self.time!r})'
