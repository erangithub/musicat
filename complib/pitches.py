import re

from .errors import SyntaxError
from .degrees import Degrees, parse_degrees

LETTERS = 'cdefgab'
NATURAL_PITCH = (0, 2, 4, 5, 7, 9, 11)

# degree 1 is c4 (middle C), the octave the parser starts at, so a plain letter
# name maps straight onto a plain degree; notes below c4 are negative
ORIGIN = 7 * 4


def parse_pitches(text):
    """Parse pitch names ('c4', 'f#', '<c4 e g>') into degrees.

    A name's octave defaults to the running one, which starts at 4 and follows
    the last name that wrote one. Inside a chord a name without an octave is
    placed above the note before it, so chords ascend.
    """
    groups = []
    min_octave = 4
    position = 0

    def note(name, octave):
        match = re.fullmatch('([a-gA-G])(b*|#*)?(-?[0-9]+)?', name)
        if not match:
            raise SyntaxError(f'Illegal pitch name "{name}"')
        run = match.group(2)
        acc = 0 if not run else (len(run) if run[0] == '#' else -len(run))
        which = int(match.group(3)) if match.group(3) else octave
        number = LETTERS.index(match.group(1).lower()) + 1 - ORIGIN + which * 7
        return number, acc, match.group(3)

    for match in re.finditer(r'<([^<>]*)>|[^<>]+', text):
        if match.start() != position:
            raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
        position = match.end()
        if match.group(1) is None:
            for name in match.group().split():
                number, acc, explicit = note(name, min_octave)
                if explicit is not None:
                    min_octave = int(explicit)
                groups.append([(number, acc)])
        else:
            names = match.group(1).split()
            if not names:
                groups.append([])
                continue
            root, root_acc, _ = note(names[0], min_octave)
            chord = [(root, root_acc)]
            running = NATURAL_PITCH[(root - 1) % 7] + 12 * ((root - 1) // 7) + root_acc
            for name in names[1:]:
                number, acc, explicit = note(name, min_octave)
                natural = NATURAL_PITCH[(number - 1) % 7] + 12 * ((number - 1) // 7) + acc
                if explicit is None:
                    while natural <= running:
                        number += 7
                        natural += 12
                chord.append((number, acc))
                running = natural
            groups.append(chord)
            min_octave = (root - 1) // 7 + ORIGIN // 7
    if position != len(text):
        raise SyntaxError(f'Illegal chord near "{text[position:].strip()}"')
    return Degrees(groups)


def format_pitches(groups, limit=None):
    """Inverse of parse_pitches: the text that parses back to `groups`.

    Every note carries its octave, so the result does not depend on the
    octave-carrying rules of the parser. With `limit`, only the first `limit`
    groups are written, followed by '… +N' (that text is for reading, not parsing).
    """
    def name(note):
        number, acc = note
        return (f'{LETTERS[(number - 1) % 7]}'
                f'{"#" * acc if acc > 0 else "b" * -acc}{(number - 1) // 7 + ORIGIN // 7}')
    shown = groups if limit is None else groups[:limit]
    tokens = []
    for group in shown:
        names = [name(note) for note in group]
        tokens.append(names[0] if len(names) == 1 else '<' + ' '.join(names) + '>')
    if len(shown) < len(groups):
        tokens.append(f'… +{len(groups) - len(shown)}')
    return ' '.join(tokens)


def major_scale(root_str):
    """The major scale on `root_str` as degrees, closing on its octave."""
    root = parse_pitches(root_str).groups[0][0]
    return Degrees(parse_degrees('1..8')).transpose(root)


def minor_scale(root_str):
    """The natural minor scale on `root_str` as degrees, closing on its octave."""
    root = parse_pitches(root_str).groups[0][0]
    return Degrees(parse_degrees('1 2 3b 4 5 6b 7b 8')).transpose(root)
