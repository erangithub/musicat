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

REST_MARKER = 'r'
LOOP_MARKER = '|:'

_TOKEN = re.compile(r'(r)?(?:(\d+)/)?(\d+)(\.*)')


def parse_rhythm(text: str) -> Rhythm:
    """Parse a rhythm such as '4 8 r4 |: 16'.

    A bare number is a fraction of a whole note ('4' is a quarter, '2' a half),
    'a/b' is a ratio ('3/4'), dots lengthen ('4.'), and an 'r' prefix makes a
    rest ('r4'). '|:' marks where the rhythm loops from once it runs out; with
    no marker the whole rhythm loops.
    """
    items = []
    seen_loop = False
    for token in text.split():
        if token == LOOP_MARKER:
            if seen_loop:
                raise SyntaxError(f'Only one loop marker "{LOOP_MARKER}" is allowed')
            seen_loop = True
            items.append(LOOP_MARKER)
            continue
        if token == ':|':
            raise SyntaxError(f'":|" is not supported: the loop started by '
                              f'"{LOOP_MARKER}" runs to the end of the rhythm')
        match = _TOKEN.fullmatch(token)
        if not match:
            raise SyntaxError(f'Illegal duration "{token}"')
        rest, numerator, denominator, dots = match.groups()
        numerator = int(numerator) if numerator is not None else 1
        denominator = int(denominator)
        if not numerator or not denominator:
            raise SyntaxError(f'Illegal duration "{token}"')
        if rest:
            items.append(REST_MARKER)
        items.append(Fraction(numerator, denominator) * (2 - Fraction(1, 2 ** len(dots))))
    if items and items[-1] == LOOP_MARKER:
        raise SyntaxError(f'Nothing to loop after "{LOOP_MARKER}"')
    return items


def rhythm_steps(rhythm: Rhythm):
    """Split a rhythm list into ([(is_rest, duration), ...], loop_start).

    loop_start is the index of the step the rhythm returns to when it runs out
    (0 when there is no loop marker, i.e. the whole rhythm loops).
    """
    steps = []
    loop_start = 0
    seen_loop = False
    i = 0
    while i < len(rhythm):
        item = rhythm[i]
        if isinstance(item, str) and item == LOOP_MARKER:
            if seen_loop:
                raise SyntaxError(f'Only one loop marker "{LOOP_MARKER}" is allowed')
            seen_loop = True
            loop_start = len(steps)
            i += 1
        elif isinstance(item, str) and item == REST_MARKER:
            if i + 1 >= len(rhythm) or isinstance(rhythm[i + 1], str):
                raise SyntaxError('Rest marker without a duration')
            steps.append((True, rhythm[i + 1]))
            i += 2
        else:
            steps.append((False, item))
            i += 1
    if seen_loop and loop_start >= len(steps):
        raise SyntaxError(f'Nothing to loop after "{LOOP_MARKER}"')
    return steps, loop_start


def rhythm_from_steps(steps, loop_start: int = 0) -> Rhythm:
    """Inverse of rhythm_steps. The loop marker is only written when the loop
    does not start at the beginning (that is the default)."""
    items = []
    for k, (rest, duration) in enumerate(steps):
        if k == loop_start and k > 0:
            items.append(LOOP_MARKER)
        if rest:
            items.append(REST_MARKER)
        items.append(duration)
    return items


def _format_duration(duration: Fraction) -> str:
    for dots in range(4):
        base = duration / (2 - Fraction(1, 2 ** dots))
        if base.numerator == 1:
            return f'{base.denominator}' + '.' * dots
    return f'{duration.numerator}/{duration.denominator}'


def format_rhythm(rhythm: Rhythm, limit=None) -> str:
    """Inverse of parse_rhythm: the text that parses back to `rhythm`.
    With `limit`, only the first `limit` tokens are written, followed by '…'."""
    tokens = []
    rest = False
    for item in rhythm:
        if isinstance(item, str) and item == LOOP_MARKER:
            tokens.append(LOOP_MARKER)
        elif isinstance(item, str) and item == REST_MARKER:
            rest = True
        else:
            tokens.append(('r' if rest else '') + _format_duration(item))
            rest = False
    if limit is not None and len(tokens) > limit:
        tokens = tokens[:limit] + ['…']
    return ' '.join(tokens)
