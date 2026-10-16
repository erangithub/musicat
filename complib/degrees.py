import re

from .errors import SyntaxError
from .pitches import Pitch

Degree = tuple[int, int]

# degree 1 is c4 (middle C), matching Pitch's default octave, so plain
# degrees need no transposition to sit in the usual range
ORIGIN = 7 * 4


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


class Degrees:
    """Scale degrees: a list of groups (a group is one note or a chord).
    """

    kind = 'degrees'

    def __init__(self, groups):
        self.groups = groups

    def __len__(self):
        return len(self.groups)

    def __iter__(self):
        return iter(self.groups)

    def __getitem__(self, index):
        return self.groups[index]

    def __eq__(self, other):
        return type(other) is Degrees and self.groups == other.groups

    def __repr__(self):
        return f"Degrees('{format_degrees(self.groups)}')"

    # ---------------------------------------------------------- palette view

    def _flat(self):
        return [note for group in self.groups for note in group]

    def _at(self, degree):
        """The (number, accidental) at `degree`, looping the palette.

        `degree` is a (number, accidental) pair.

        A palette's groups are flattened. All but the last note form the unit
        that repeats; the last note is a marker whose interval above the first
        note is the period, so `c d e` repeats as `c d | e f | g a | b c ...`.
        A single-note palette has period zero and just returns that note.
        """
        step, acc = degree
        notes = self._flat()
        if not notes:
            raise SyntaxError('Empty palette')
        if len(notes) == 1:
            number, base_acc = notes[0]
            return (number, base_acc + acc)
        unit = notes[:-1]
        period_number = notes[-1][0] - notes[0][0]
        period_acc = notes[-1][1] - notes[0][1]
        cycles, index = divmod(step - 1, len(unit))
        number, base_acc = unit[index]
        return (number + cycles * period_number, base_acc + cycles * period_acc + acc)

    def _degree_of(self, number, acc=0, strict=False):
        """Inverse of `_at`: the (degree, accidental) that `_at` maps here.

        Spelling is preserved: a degree is chosen whose letter matches. If the
        palette has several such degrees the one needing the smallest accidental
        wins, then the lowest degree. If no degree shares the letter the nearest
        degree by sound is used (round-tripping the sound, not the spelling).
        With strict=True a note that is not exactly a palette note raises.
        """
        notes = self._flat()
        if not notes:
            raise SyntaxError('Empty palette')
        name = format_degrees([[(number, acc)]])
        if len(notes) == 1:
            base, base_acc = notes[0]
            residual = acc - base_acc
            if strict and residual:
                raise SyntaxError(f'{name} is not in the palette')
            return (1, residual)
        unit = notes[:-1]
        period_number = notes[-1][0] - notes[0][0]
        period_acc = notes[-1][1] - notes[0][1]
        length = len(unit)
        best = None
        for i, (base, base_acc) in enumerate(unit):
            if period_number:
                diff = number - base
                if diff % period_number:
                    continue
                q = diff // period_number
            elif number == base:
                if period_acc:
                    diff_acc = acc - base_acc
                    if diff_acc % period_acc:
                        continue
                    q = diff_acc // period_acc
                else:
                    q = 0
            else:
                continue
            degree = i + 1 + q * length
            residual = acc - (base_acc + q * period_acc)
            if best is None or (abs(residual), degree) < (abs(best[1]), best[0]):
                best = (degree, residual)
        if best is not None:
            if strict and best[1]:
                raise SyntaxError(f'{name} is not in the palette')
            return best

        raise SyntaxError(f'{name} is not in the palette')

    # ------------------------------------------------------------ operations

    def compose(self, other):
        """`self` seen in `other`: every degree resolved/selected through the
        palette `other`. Chords of `self` are kept; `other`'s groups are flat."""
        if not isinstance(other, Degrees):
            raise SyntaxError(f'Cannot compose with {other!r}: expected degrees')
        return Degrees([[other._at(degree) for degree in group]
                        for group in self.groups])

    def decompose(self, other, strict=False):
        """`self`'s notes as (degree, accidental) in the palette `other`."""
        if not isinstance(other, Degrees):
            raise SyntaxError(f'Cannot decompose against {other!r}: expected degrees')
        return Degrees([[other._degree_of(number, acc, strict)
                         for number, acc in group] for group in self.groups])

    def stack(self, other):
        """Stack another degree pattern on top of this one (interval addition)."""
        return Degrees(stack_degrees(self.groups, other.groups))

    def transpose(self, interval, palette=None):
        """Move every note by a degree `interval` through a plane.

        `interval` is a (number, accidental) degree, a one-note Degrees, or a
        string in the degrees syntax. A string may start with '-' to go down,
        so '4#' is up a sharp fourth and '-4#' is down one.

        Two degrees add as `P(a) + a'` plus `P(b) + b'` minus `P(a + b - 1)`
        minus `P(1)`, where `P` is the plane's value at a degree. The plane is
        the white keys by default; pass another palette to measure elsewhere.
        """
        if palette is None:
            palette = white_keys
        if not isinstance(palette, Degrees):
            raise SyntaxError(f'Cannot transpose through {palette!r}: expected degrees')
        down = False
        if isinstance(interval, str):
            text = interval.strip()
            down = text.startswith('-')
            step, acc = _parse_degree(text[1:] if down else text)
        elif isinstance(interval, Degrees):
            flat = interval._flat()
            if len(flat) != 1:
                raise SyntaxError(f'An interval must be one degree, not {interval!r}')
            step, acc = flat[0]
        elif isinstance(interval, tuple) and len(interval) == 2:
            step, acc = interval
        else:
            raise SyntaxError(f'Illegal interval {interval!r}')

        if down:
            value = palette._at((step, 0))[0] + acc
            step = 2 - step
            acc = -value - palette._at((step, 0))[0]

        groups = []
        for group in self.groups:
            notes = []
            for s1, a1 in group:
                offset = (palette._at((s1, 0))[0] + palette._at((step, 0))[0]
                          - palette._at((s1 + step - 1, 0))[0] - palette._at((1, 0))[0])
                notes.append((s1 + step - 1, a1 + acc + offset))
            groups.append(notes)
        return Degrees(groups)

    def pitch(self):
        """These degrees as concrete pitches (the I/O value), groups kept."""
        result = []
        for group in self.groups:
            notes = []
            for number, acc in group:
                pitch = Pitch()
                pitch.idx = number - 1 + ORIGIN
                pitch.acc = acc
                notes.append(pitch)
            result.append(notes)
        return result

    def __rshift__(self, other):
        return self.compose(other)

    def __lshift__(self, other):
        return self.decompose(other)

def major_scale(root_str):
    root = Pitch(root_str)
    names = ('c', 'd', 'e', 'f', 'g', 'a', 'b')
    notes = [root + Pitch(name, 0) for name in names]
    notes.append(root + Pitch('c', 1))            # close the octave (the period marker)
    return Degrees([[(pitch.idx + 1 - ORIGIN, pitch.acc)] for pitch in notes])


def minor_scale(root_str):
    root = Pitch(root_str)
    names = ('c', 'd', 'eb', 'f', 'g', 'ab', 'bb')
    notes = [root + Pitch(name, 0) for name in names]
    notes.append(root + Pitch('c', 1))            # close the octave (the period marker)
    return Degrees([[(pitch.idx + 1 - ORIGIN, pitch.acc)] for pitch in notes])


# the plane transpose measures through by default: the white keys, whose degrees
# are semitones (the closing 12 is the period marker)
white_keys = Degrees(parse_degrees('0 2 4 5 7 9 11 12'))
