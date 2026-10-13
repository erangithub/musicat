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

def parse_degrees(text):
    groups = []
    group = []
    position = 0
    in_chord = False
    in_range = False
    in_step = None

    for match in re.finditer(r'(<)|(>)|(-?\d+(?:b+|#+)?)(?!:)|(\.\.)|(\d+):|\s+', text):
        print(match)
        if match.start() != position:
            raise SyntaxError(f'Syntax error near "{text[position:].strip()}"')
        if match.group(1) is not None:
            if in_range or in_chord:
                raise SyntaxError(f'Illegal symbol near"{text[position:].strip()}"')
            in_chord = True
            group = []
        elif match.group(2) is not None:
            if not in_chord:
                raise SyntaxError(f'Illegal symbol near"{text[position:].strip()}"')
            if group == []:
                raise SyntaxError(f'Empty chord near "{text[position:].strip()}"')
            groups.append(group)
            group = []
            in_chord = False
        elif match.group(3) is not None:
            d, acc = _parse_degree(match.group(3))
            if in_range:
                (prev_d,_) = groups[-1][0]
                step = 1 if d > prev_d else -1
                if in_step:
                    step *= in_step
                for k in range(prev_d+step, d, step):
                   groups.append([(k,0)])
                in_range = False
                in_step = None
            group.append((d, acc))
            if not in_chord:
                groups.append(group)
                group = []
        elif match.group(4) is not None:
            if in_range or groups == 0 or len(groups[-1]) != 1:
                raise SyntaxError(f'Illegal symbol near"{text[position:].strip()}"')
            in_range = True
        elif match.group(5) is not None:
            if in_step:
                raise SyntaxError(f'Illegal symbol near"{text[position:].strip()}"')
            in_step = int(match.group(5))
        position = match.end()
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
