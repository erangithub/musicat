import re

from .errors import SyntaxError

Degree = tuple[int, int]

def parse_degrees(text):
    groups = []
    position = 0
    for match in re.finditer(r'<([^<>]*)>|[^<>]+', text):
        if match.start() != position:
            raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
        position = match.end()
        if match.group(1) is None:
            units = [[name] for name in match.group().split()]
        else:
            units = [match.group(1).split()]
        for names in units:
            group = []
            for name in names:
                degree = re.fullmatch(r'(-?\d+)(b*|#*)?', name)
                if not degree:
                    raise SyntaxError(f'Illegal degree "{name}"')
                accidental = degree.group(2)
                if not accidental:
                    acc = 0
                elif accidental[0] == '#':
                    acc = len(accidental)
                else:
                    acc = -len(accidental)
                group.append((int(degree.group(1)), acc))
            groups.append(group)
    if position != len(text):
        raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
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

