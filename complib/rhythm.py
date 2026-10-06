import re
from fractions import Fraction

from .errors import SyntaxError

WHOLE = Fraction(1)
HALF = Fraction(1, 2)
QUARTER = Fraction(1, 4)
EIGHTH = Fraction(1, 8)
SIXTEENTH = Fraction(1, 16)
THIRTY_SECOND = Fraction(1, 32)
DOT = Fraction(3, 2)
DOUBLE_DOT = Fraction(7, 4)

Duration = Fraction
Rhythm = list[Duration]


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
