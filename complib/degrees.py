import re

from .errors import SyntaxError

Degree = tuple[int, int]


def _parse_degree(text):
    degree = re.fullmatch(r'(-?\d+)(b+|#+)?', text)
    if not degree:
        raise SyntaxError(f'Illegal degree "{text}"')
    accidental = degree.group(2)
    if not accidental:
        acc = 0
    elif accidental[0] == '#':
        acc = len(accidental)
    else:
        acc = -len(accidental)
    return (int(degree.group(1)), acc)


# <  >  ..  step:  degree  whitespace.  The step is tried before the degree so that
# '10:' is a step and not the degree '1'; a degree may not run straight into
# another digit or a minus sign ('1b2', '5-3').
_TOKEN = re.compile(r'(<)|(>)|(\.\.)|(\d+):|(-?\d+(?:b+|#+)?)(?![-\d])|\s+')


def parse_degrees(text):
    """Parse degrees such as '1 3 5', '<1 3 5>', and ranges.

    A range 'a..b' fills in the degrees between a and b (stepping up or down as
    needed), 'a..s:b' steps by s, and 'a..b..c' goes through waypoint b. The
    first and last degree keep their accidentals, the ones in between have none,
    and the end is always included even if the step does not land on it
    ('1..4:10' is 1 5 9 10). Ranges are not allowed inside a chord.
    """
    groups = []
    group = []
    position = 0
    in_chord = False
    in_range = False
    in_step = None

    for match in _TOKEN.finditer(text):
        rest = text[match.start():].strip()
        if match.start() != position:
            raise SyntaxError(f'Syntax error near "{text[position:].strip()}"')
        if match.group(1) is not None:                      # <
            if in_range or in_chord:
                raise SyntaxError(f'Illegal symbol near "{rest}"')
            in_chord = True
            group = []
        elif match.group(2) is not None:                    # >
            if not in_chord:
                raise SyntaxError(f'Illegal symbol near "{rest}"')
            if group == []:
                raise SyntaxError(f'Empty chord near "{rest}"')
            groups.append(group)
            group = []
            in_chord = False
        elif match.group(3) is not None:                    # ..
            if in_chord:
                raise SyntaxError(f'A range cannot be inside a chord, near "{rest}"')
            if in_range or not groups or len(groups[-1]) != 1:
                raise SyntaxError(f'Illegal symbol near "{rest}"')
            in_range = True
        elif match.group(4) is not None:                    # step:
            if not in_range or in_step is not None:
                raise SyntaxError(f'Illegal step near "{rest}"')
            in_step = int(match.group(4))
            if in_step == 0:
                raise SyntaxError(f'A range cannot have a step of 0, near "{rest}"')
        elif match.group(5) is not None:                    # degree
            d, acc = _parse_degree(match.group(5))
            if in_range:
                (prev_d, _) = groups[-1][0]
                step = 1 if d > prev_d else -1
                if in_step:
                    step *= in_step
                for k in range(prev_d + step, d, step):
                    groups.append([(k, 0)])
                in_range = False
                in_step = None
            group.append((d, acc))
            if not in_chord:
                groups.append(group)
                group = []
        position = match.end()
    if position != len(text):
        raise SyntaxError(f'Syntax error near "{text[position:].strip()}"')
    if in_chord:
        raise SyntaxError('Unterminated chord: missing ">"')
    if in_range:
        raise SyntaxError('A range needs an end, as in "1..5"')
    return groups


def stack_degrees(pattern1 : list[Degree], pattern2 : list[Degree]):
    result = []

    for c2 in pattern2:
        for c1 in pattern1:
            res_chord = []
            for d2, a2 in c2:
                for d1, a1 in c1:
                    res_chord.append((d1+d2-1, a1+a2))
            result.append(res_chord)

    return result


def format_degrees(groups, limit=None):
    """Inverse of parse_degrees: the text that parses back to `groups`.
    With `limit`, only the first `limit` groups are written, followed by '… +N'."""
    def name(degree):
        number, acc = degree
        return f'{number}{"#" * acc if acc > 0 else "b" * -acc}'
    shown = groups if limit is None else groups[:limit]
    tokens = []
    for group in shown:
        names = [name(degree) for degree in group]
        tokens.append(names[0] if len(names) == 1 else '<' + ' '.join(names) + '>')
    if len(shown) < len(groups):
        tokens.append(f'… +{len(groups) - len(shown)}')
    return ' '.join(tokens)
