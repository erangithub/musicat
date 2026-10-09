import re

from .errors import SyntaxError


def to_degrees(text):
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
                degree = re.fullmatch(r'(\d+)(b*|#*)?', name)
                if not degree or int(degree.group(1)) < 1:
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
