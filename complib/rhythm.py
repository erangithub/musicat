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
Rhythm = list[Duration | str]

REST_MARKER = '_'
LOOP_MARKER = 'L'

def parse_rhythm(text : str) -> Rhythm:
    tokens = text.split()
    durations = []
    for token in tokens:
        match = re.fullmatch(r'(_)?(\d*)(?:/(\d+))?(\.*)', token)
        if not match:
            raise SyntaxError(f'Illegal duration "{token}"')
        rest, numerator, denominator, dots = match.group(1), match.group(2), match.group(3), match.group(4)
        if not numerator and denominator is None:
            raise SyntaxError(f'Illegal duration "{token}"')
        if denominator is None:
            duration = Fraction(int(numerator))
        else:
            denominator = int(denominator)
            if not denominator:
                raise SyntaxError(f'Illegal duration "{token}"')
            duration = Duration(int(numerator or 1), denominator)
        if rest:
            durations.append(REST_MARKER)
        durations.append(duration * (2 - Fraction(1, 2 ** len(dots))))
    return durations
