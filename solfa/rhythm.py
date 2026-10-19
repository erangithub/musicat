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
OPEN_MARKER = '['

_HEADER = re.compile(r'(\d+):(\d*)')
_REPEAT = re.compile(r'\*(\d+)$')
_PART = re.compile(r'(\d+)(\.*)')


def parse_rhythm(text: str) -> Rhythm:
    """Parse a rhythm such as '4 8 r4 [16'.

    A bare number is a fraction of a whole note ('4' is a quarter, '2' a half),
    dots lengthen it ('4.' is dotted, '4..' double-dotted) and an 'r' prefix
    makes it a rest ('r4'). A '+'-joined chain of numbers is one longer event
    ('4+8' is a dotted quarter). A trailing '*n' repeats a token ('8*3' is
    '8 8 8'), and '[...]' groups, which nest and may themselves be repeated, are
    expanded away. An unclosed '[' is a cycling tail: everything before it plays
    once and everything after it repeats ('4 [8' is a quarter then eighths
    forever). A '[...]' right after '[' is a tuplet, '[k:' sitting in the time of
    the largest power of two below k ('[3: 8 8 8]', '[5: 16*5]'), and '[k:j'
    overrides that ration ('[7:8 16*7]').
    """
    items = []
    stack = []
    for token in text.split():
        if token == '|:':
            raise SyntaxError('"|:" is gone; write the cycle as an open group, '
                              'e.g. "4 [8"')
        opens = 0
        while token.startswith(OPEN_MARKER):
            token = token[1:]
            opens += 1
        multiplier = None
        if opens:
            header = _HEADER.match(token)
            if header:
                k = int(header.group(1))
                j = int(header.group(2)) if header.group(2) else None
                if k < 1 or (j is not None and j < 1):
                    raise SyntaxError(f'Illegal tuplet "{token}"')
                if j is None:
                    j = 1
                    while j * 2 <= k:
                        j *= 2
                multiplier = Fraction(j, k)
                token = token[header.end():]
        closes = 0
        repeat = None
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
        for op in suffix:
            if op != 'close':
                repeat = op[1]
                break
        if repeat is not None and repeat < 1:
            raise SyntaxError('A repeat count must be a positive integer')
        for _ in range(opens):
            stack.append([None, []])
        if multiplier is not None:
            stack[-1][0] = multiplier
        if token:
            if '[' in token or ']' in token:
                raise SyntaxError(f'Illegal duration "{token}"')
            rest = token.startswith(REST_MARKER)
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
            if closes > 0 and repeat is not None and suffix[0] != 'close':
                body_repeat = 1
            else:
                body_repeat = repeat if repeat is not None else 1
            target = stack[-1][1] if stack else items
            for _ in range(body_repeat):
                if rest:
                    target.append(REST_MARKER)
                target.append(total)
        elif repeat is not None and closes == 0:
            raise SyntaxError(f'Nothing to repeat with "*{repeat}"')
        group_repeat = (repeat if repeat is not None and closes > 0
                        and suffix[0] != 'close' else 1)
        closed = []
        for _ in range(closes):
            if not stack:
                raise SyntaxError('Unmatched "]"')
            frame_multiplier, frame_items = stack.pop()
            if frame_multiplier is not None and frame_multiplier != 1:
                frame_items = [REST_MARKER if item == REST_MARKER
                               else item * frame_multiplier
                               for item in frame_items]
            destination = stack[-1][1] if stack else items
            destination.extend(frame_items)
            closed.append((destination, frame_items))
        if group_repeat != 1:
            destination, frame_items = closed[-1]
            for _ in range(group_repeat - 1):
                destination.extend(frame_items)
    if len(stack) > 1:
        raise SyntaxError('Only one group may be left open at the end')
    if len(stack) == 1:
        multiplier, frame_items = stack[0]
        if multiplier is not None and multiplier != 1:
            frame_items = [REST_MARKER if item == REST_MARKER
                           else item * multiplier for item in frame_items]
        if not frame_items:
            raise SyntaxError('Nothing to cycle after "["')
        items = items + [OPEN_MARKER] + frame_items
    return items


def rhythm_steps(rhythm: Rhythm):
    """Split a rhythm list into ([(is_rest, duration), ...], loop_start).

    loop_start is the index of the step the rhythm cycles back to when it runs
    out of content, or None when nothing is marked to cycle (the rhythm then
    plays once on its own and simply repeats from the start over content).
    """
    steps = []
    loop_start = None
    i = 0
    while i < len(rhythm):
        item = rhythm[i]
        if isinstance(item, str) and item == OPEN_MARKER:
            if loop_start is not None:
                raise SyntaxError('Only one open group "[" is allowed')
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
    if loop_start is not None and loop_start >= len(steps):
        raise SyntaxError('Nothing to cycle after "["')
    return steps, loop_start


def rhythm_from_steps(steps, loop_start: int | None = None) -> Rhythm:
    """Inverse of rhythm_steps. An open marker is only written when the cycle is
    explicit (loop_start is not None); the rhythm otherwise stays flat."""
    items = []
    for k, (rest, duration) in enumerate(steps):
        if k == loop_start:
            items.append(OPEN_MARKER)
        if rest:
            items.append(REST_MARKER)
        items.append(duration)
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
    With `limit`, only the first `limit` tokens are written, followed by '…'."""
    tokens = []
    rest = False
    pending_open = False
    for item in rhythm:
        if isinstance(item, str) and item == OPEN_MARKER:
            pending_open = True
        elif isinstance(item, str) and item == REST_MARKER:
            rest = True
        else:
            token = ('r' if rest else '') + _format_duration(item)
            if pending_open:
                token = OPEN_MARKER + token
                pending_open = False
            tokens.append(token)
            rest = False
    if pending_open:
        tokens.append(OPEN_MARKER)
    if limit is not None and len(tokens) > limit:
        tokens = tokens[:limit] + ['…']
    return ' '.join(tokens)
