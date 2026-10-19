import re

from .errors import SyntaxError
from .degrees import Degrees, parse_degrees

LETTERS = 'cdefgab'

# degree 1 is c4 (middle C), the octave the parser starts at, so a plain letter
# name maps straight onto a plain degree; notes below c4 are negative
ORIGIN = 7 * 4


def parse_pitches(text):
    """Parse pitch names ('c4', 'f#', '<c4 e g>') into degrees.

    A name's octave defaults to the running one, which starts at 4 and follows
    the last name that wrote one, whether inside a chord or not.
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
        chord = match.group(1) is not None
        names = (match.group(1) if chord else match.group()).split()
        notes = []
        for name in names:
            number, acc, explicit = note(name, min_octave)
            if explicit is not None:
                min_octave = int(explicit)
            notes.append((number, acc))
        if chord:
            groups.append(notes)
        else:
            groups.extend([note] for note in notes)
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
        acc = acc or 0
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
    """The major scale on `root_str` as an idea, closing on its octave."""
    from .idea import Idea
    p, acc = parse_pitches(root_str).groups[0][0]
    letter = ((p - 1) % 7) + 1
    shift = 7 * ((p - 1) // 7)          # whole octaves down to the root's octave
    return Idea(Degrees(parse_degrees('1..8')).diatonic(shift + 1)
                                   .transpose((letter, acc)))


def minor_scale(root_str):
    """The natural minor scale on `root_str` as an idea, closing on its octave."""
    from .idea import Idea
    p, acc = parse_pitches(root_str).groups[0][0]
    letter = ((p - 1) % 7) + 1
    shift = 7 * ((p - 1) // 7)          # whole octaves down to the root's octave
    return Idea(Degrees(parse_degrees('1 2 3b 4 5 6b 7b 8')).diatonic(shift + 1)
                                        .transpose((letter, acc)))
