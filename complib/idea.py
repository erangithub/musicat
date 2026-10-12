from .errors import SyntaxError
from .pitches import parse_pitches
from .degrees import parse_degrees, stack_degrees
from .rhythm import parse_rhythm, REST_MARKER, WHOLE

class Idea:
    def __init__(self, pitches=None, degrees=None, rhythm=None):
        if pitches is not None and degrees is not None:
            raise SyntaxError('Idea cannot have both pitches and degrees')
        self.pitches = pitches
        self.degrees = degrees
        self.rhythm = rhythm

    def __eq__(self, other):
        return (isinstance(other, Idea)
                and self.pitches == other.pitches
                and self.degrees == other.degrees
                and self.rhythm == other.rhythm)

    def __repr__(self):
        fields = ', '.join(
            f'{name}={value!r}' for name in ('pitches', 'degrees', 'rhythm')
            if (value := getattr(self, name)) is not None)
        return f'Idea({fields})'

    def __add__(self, other):
        if not isinstance(other, Idea):
            raise SyntaxError(f'Illegal operand {other!r}')
        for name in ('pitches', 'degrees', 'rhythm'):
            mine = getattr(self, name)
            if mine is not None and getattr(other, name) is not None:
                raise SyntaxError(f'Cannot combine ideas that share {name}')
        return Idea(
            pitches=self.pitches if self.pitches is not None else other.pitches,
            degrees=self.degrees if self.degrees is not None else other.degrees,
            rhythm=self.rhythm if self.rhythm is not None else other.rhythm)

    def __mul__(self, other):
        if not isinstance(other, Idea):
            raise SyntaxError(f'Illegal operand {other!r}')

        if getattr(self, 'rhythm') is not None and getattr(other, 'rhythm') is not None:
            raise SyntaxError(f'Cannot combine ideas that share rhythm')

        if getattr(self, 'degrees') is None:
            raise SyntaxError(f"Cannot stack ideas that don't have degrees")

        if getattr(other, 'degrees') is None:
            raise SyntaxError(f"Cannot stack ideas that don't have degrees")

        return Idea(
            degrees=stack_degrees(self.degrees, other.degrees),
            rhythm=self.rhythm if self.rhythm is not None else other.rhythm)

    def as_pitches(self, palette):
        if self.degrees is None:
            raise SyntaxError('An idea without degrees has no pitches to resolve')
        pitches = [[palette.at(number, acc) for number, acc in group]
                   for group in self.degrees]
        return Idea(pitches=pitches, rhythm=self.rhythm)

    def __len__(self):
        if self.pitches is not None:
            return len(self.pitches)
        elif self.degrees is not None:
            return len(self.degrees)
        elif self.rhythm is not None:
            return len(self.rhythm)
        else:
            return 0

    def show(self, time='4/4'):
        from . import Part
        Part(self).show(time)

    def events(self):
        rhythm = self.rhythm or [WHOLE]
        pitches = self.pitches
        result = []
        j = 0
        i = 0
        len_r = len(rhythm)
        len_p = len(pitches) if pitches else 0
        while i < (len_p or len_r):
            if rhythm[j] == REST_MARKER:
                result.append(([], rhythm[j+1]))
                j = (j+2) % len_r
                continue
            else:
                if len_p:
                    result.append((pitches[i], rhythm[j]))
                    i = i+1
                else:
                    result.append(([], rhythm[j]))
                j = (j+1) % len_r
            if j == 0 and len_p == 0:
                break
        return result

def pitches(text):
    return Idea(pitches = parse_pitches(text))

def degrees(text):
    return Idea(degrees = parse_degrees(text))

def rhythm(text):
    return Idea(rhythm = parse_rhythm(text))
