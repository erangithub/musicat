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


class OpenMarker:
    """Open a group. A bare marker (k is None) only marks the cycling tail; a
    tuplet marker carries the ratio j/k its notes are played in."""

    def __init__(self, k=None, j=None):
        self.k = k
        self.j = j

    def __eq__(self, other):
        return (isinstance(other, OpenMarker)
                and self.k == other.k and self.j == other.j)

    def __hash__(self):
        return hash((OpenMarker, self.k, self.j))

    def __repr__(self):
        return ('OpenMarker()' if self.k is None
                else f'OpenMarker({self.k}, {self.j})')


class CloseMarker:
    def __eq__(self, other):
        return isinstance(other, CloseMarker)

    def __hash__(self):
        return hash(CloseMarker)

    def __repr__(self):
        return 'CloseMarker()'


class RestMarker:
    def __init__(self, duration):
        self.duration = duration

    def __eq__(self, other):
        return isinstance(other, RestMarker) and self.duration == other.duration

    def __hash__(self):
        return hash((RestMarker, self.duration))

    def __repr__(self):
        return f'RestMarker({self.duration})'


Duration = Fraction
Element = Fraction | OpenMarker | CloseMarker | RestMarker
Rhythm = list[Element]

_HEADER = re.compile(r'(\d+):')
_REPEAT = re.compile(r'\*(\d+)$')
_PART = re.compile(r'(\d+)(\.*)')


def parse_rhythm(text: str) -> Rhythm:
    """Parse a rhythm such as '4 8 r4 [16'.

    A bare number is a fraction of a whole note ('4' is a quarter, '2' a half),
    dots lengthen it ('4.' is dotted, '4..' double-dotted) and an 'r' prefix
    makes it a rest ('r4'). A '+'-joined chain of numbers is one longer event
    ('4+8' is a dotted quarter). A trailing '*n' repeats a token ('8*3' is
    '8 8 8'), and '[...]' groups, which nest and may themselves be repeated,
    are expanded away. A 'k:' right after '[' is a tuplet, its notes sitting in
    the time of the largest power of two below k ('[3: 8 8 8]', '[5: 16*5]');
    write 'k j:' to override that ratio ('[7 8: 16*7]'). Durations are stored
    as written, relative to the tuplet they sit in. An unclosed '[' is a
    cycling tail: everything before it plays once and everything after it
    repeats ('4 [8' is a quarter then eighths forever); when brackets nest
    unclosed it is the innermost one that loops.
    """
    items = []
    stack = []                              # frames: [k, j, items]
    tokens = text.split()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if token == '|:':
            raise SyntaxError('"|:" is gone; write the cycle as an open group, '
                              'e.g. "4 [8"')
        opens = 0
        while token.startswith('['):
            token = token[1:]
            opens += 1
        k = j = None
        if opens:
            header = _HEADER.match(token)
            if header:
                shown = header.group(0)
                k = int(header.group(1))
                token = token[header.end():]
            elif token.isdigit() and i < len(tokens) \
                    and tokens[i].endswith(':') and tokens[i][:-1].isdigit():
                shown = f'{token} {tokens[i]}'
                k, j = int(token), int(tokens[i][:-1])
                token = ''
                i += 1
            if k is not None:
                if k < 1 or (j is not None and j < 1):
                    raise SyntaxError(f'Illegal tuplet "{shown}"')
                if j is None:
                    j = 1
                    while j * 2 <= k:
                        j *= 2
        suffix = []
        while True:
            if token.endswith(']'):
                suffix.append('close')
                token = token[:-1]
                continue
            cover = _REPEAT.search(token)
            if not cover:
                break
            suffix.append(('repeat', int(cover.group(1))))
            token = token[:cover.start()]
        closes = suffix.count('close')
        # suffix was read right-to-left; in written order the repeats before the
        # first ']' multiply the duration itself, the ones after it multiply the
        # group that ']' closes ('[3: 8*3]*2' is three eighths, twice over)
        body_repeat = group_repeat = 1
        closed = False
        for op in reversed(suffix):
            if op == 'close':
                closed = True
            elif closed:
                group_repeat *= op[1]
            else:
                body_repeat *= op[1]
        for op in suffix:
            if op != 'close' and op[1] < 1:
                raise SyntaxError('A repeat count must be a positive integer')
        for _ in range(opens):
            stack.append([None, None, []])
        if k is not None:
            stack[-1][0] = k
            stack[-1][1] = j
        if token:
            if '[' in token or ']' in token:
                raise SyntaxError(f'Illegal duration "{token}"')
            rest = token.startswith('r')
            if rest:
                token = token[1:]
            total = Fraction(0)
            for part in token.split('+'):
                match = _PART.fullmatch(part)
                if not match:
                    raise SyntaxError(f'Illegal duration "{part}"')
                number = int(match.group(1))
                if number < 1:
                    raise SyntaxError(f'Illegal duration "{part}"')
                dots = match.group(2)
                total += Fraction(1, number) * (2 - Fraction(1, 2 ** len(dots)))
            target = stack[-1][2] if stack else items
            for _ in range(body_repeat):
                target.append(RestMarker(total) if rest else total)
        elif body_repeat != 1 and closes == 0:
            raise SyntaxError(f'Nothing to repeat with "*{body_repeat}"')
        blocks = []
        for _ in range(closes):
            if not stack:
                raise SyntaxError('Unmatched "]"')
            fk, fj, fitems = stack.pop()
            if fk is not None:
                block = [OpenMarker(fk, fj)] + fitems + [CloseMarker()]
            else:
                block = fitems
            destination = stack[-1][2] if stack else items
            destination.extend(block)
            blocks.append((destination, block))
        if group_repeat != 1:
            destination, block = blocks[-1]
            for _ in range(group_repeat - 1):
                destination.extend(block)
    if stack:
        innermost = len(stack) - 1
        if not stack[-1][2]:
            raise SyntaxError('Nothing to cycle after "["')
        for depth, (fk, fj, fitems) in enumerate(stack):
            if fk is not None:
                items.append(OpenMarker(fk, fj))
            elif depth == innermost:
                items.append(OpenMarker())
            items.extend(fitems)
    return items


def _format_duration(duration: Fraction) -> str:
    for dots in range(4):
        base = duration / (2 - Fraction(1, 2 ** dots))
        if base.numerator == 1:
            return f'{base.denominator}' + '.' * dots
    parts = []
    remaining = duration
    while remaining > 0:
        denominator = -(-remaining.denominator // remaining.numerator)
        parts.append(f'{denominator}')
        remaining -= Fraction(1, denominator)
    return '+'.join(parts)


def format_rhythm(rhythm: Rhythm, limit=None) -> str:
    """Inverse of parse_rhythm: the text that parses back to `rhythm`.
    With `limit`, only the first `limit` duration tokens are written, followed
    by '…'."""
    tokens = []
    prefix = ''
    for item in rhythm:
        if isinstance(item, OpenMarker):
            if item.k is None:
                prefix += '['
            else:
                default = 1 << (item.k.bit_length() - 1)
                header = (f'[{item.k}:' if item.j == default
                          else f'[{item.k} {item.j}:')
                tokens.append(prefix + header)
                prefix = ''
        elif isinstance(item, CloseMarker):
            if tokens:
                tokens[-1] += ']'
            else:
                prefix += ']'
        elif isinstance(item, RestMarker):
            tokens.append(prefix + 'r' + _format_duration(item.duration))
            prefix = ''
        else:
            tokens.append(prefix + _format_duration(item))
            prefix = ''
    if prefix:
        tokens.append(prefix)
    if limit is not None:
        kept = []
        shown = 0
        for token in tokens:
            if not token.endswith(':') and any(ch.isdigit() for ch in token):
                if shown == limit:
                    break
                shown += 1
            kept.append(token)
        if shown == limit and len(kept) < len(tokens):
            kept.append('…')
        tokens = kept
    return ' '.join(tokens)
