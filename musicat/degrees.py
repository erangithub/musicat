import re

from .errors import SyntaxError

Degree = tuple[int, int | None]


def _parse_degree(text):
    degree = re.fullmatch(r'(-?\d+)(n|b+|#+)?', text)
    if not degree:
        raise SyntaxError(f'Illegal degree "{text}"')
    accidental = degree.group(2)
    if accidental is None:
        acc = None                       # scale-relative: the palette decides
    elif accidental == 'n':
        acc = 0                          # explicitly natural
    elif accidental[0] == '#':
        acc = len(accidental)
    else:
        acc = -len(accidental)
    return (int(degree.group(1)), acc)


# <  >  ..  step:  degree  whitespace.  The step is tried before the degree so that
# '10:' is a step and not the degree '1'; a degree may not run straight into
# another digit or a minus sign ('1b2', '5-3').
_TOKEN = re.compile(r'(<)|(>)|(\.\.)|(,,)|(\d+):|(-?\d+(?:n|b+|#+)?)(?![-\d])|\s+')


def parse_degrees(text):
    """Parse degrees such as '1 3 5', '<1 3 5>', and ranges.

    A bare number is scale-relative — its accidental is None, left to the
    palette to decide — while '4n', '4#' and '4b' carry a final accidental:
    0, 1 and -1. A range 'a..b' fills in the degrees between a and b (stepping
    up or down as needed), 'a..s:b' steps by s, and 'a..b..c' goes through
    waypoint b. The first and last degree keep their accidentals, the ones in
    between are bare, and the end is always included even if the step does not
    land on it ('1..4:10' is 1 5 9 10). Ranges are not allowed inside a chord.
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
        elif match.group(4) is not None:                    # ,, (range w/ step 2 default)
            if in_chord:
                raise SyntaxError(f'A range cannot be inside a chord, near "{rest}"')
            if in_range or not groups or len(groups[-1]) != 1:
                raise SyntaxError(f'Illegal symbol near "{rest}"')
            in_range = True
            in_step = 2
        elif match.group(5) is not None:                    # step:
            if not in_range or in_step is not None:
                raise SyntaxError(f'Illegal step near "{rest}"')
            in_step = int(match.group(5))
            if in_step == 0:
                raise SyntaxError(f'A range cannot have a step of 0, near "{rest}"')
        elif match.group(6) is not None:                    # degree
            d, acc = _parse_degree(match.group(6))
            if in_range:
                (prev_d, _) = groups[-1][0]
                step = 1 if d > prev_d else -1
                if in_step:
                    step *= in_step
                for k in range(prev_d + step, d, step):
                    groups.append([(k, None)])
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


def compose_degrees(pattern1 : list[Degree], pattern2 : list[Degree]):
    result = []

    for c1 in pattern1:
        for c2 in pattern2:
            res_chord = []
            for d1, a1 in c1:
                for d2, a2 in c2:
                    acc = None if a1 is None and a2 is None else (a1 or 0) + (a2 or 0)
                    res_chord.append((d1+d2-1, acc))
            result.append(res_chord)

    return result


def format_degrees(groups, limit=None):
    """Inverse of parse_degrees: the text that parses back to `groups`.
    With `limit`, only the first `limit` groups are written, followed by '… +N'."""
    def name(degree):
        number, acc = degree
        if acc is None:
            return f'{number}'
        return f'{number}{"n" if acc == 0 else "#" * acc if acc > 0 else "b" * -acc}'
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

        `degree` is a (number, accidental) pair; either part may be None,
        meaning no accidental is imposed. A bare palette note stays bare.

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
            shift = 0
        else:
            unit = notes[:-1]
            period_number = notes[-1][0] - notes[0][0]
            period_acc = ((notes[-1][1] or 0) - (notes[0][1] or 0))
            cycles, index = divmod(step - 1, len(unit))
            number, base_acc = unit[index]
            number += cycles * period_number
            shift = cycles * period_acc
        if base_acc is None and acc is None and not shift:
            return (number, None)
        return (number, (base_acc or 0) + (acc or 0) + shift)

    def _degree_of(self, number, acc=0, strict=False):
        """Inverse of `_at`: the (degree, accidental) that `_at` maps here.

        The accidental is final, like everywhere: a note that is exactly a
        palette note comes back bare — None, what the scale wants — and any
        other note keeps its own accidental, so mapping it back reproduces it.
        Spelling is preserved: a degree is chosen whose letter matches. If the
        palette has several such degrees the one needing the smallest
        accidental wins, then the lowest degree. A note sharing no letter with
        the palette has no degree, and with strict=True a note that is not
        exactly a palette note raises.
        """
        if acc is None:
            acc = 0
        notes = self._flat()
        if not notes:
            raise SyntaxError('Empty palette')
        name = format_degrees([[(number, acc)]])
        if len(notes) == 1:
            base, base_acc = notes[0]
            base_acc = base_acc or 0
            if strict and acc != base_acc:
                raise SyntaxError(f'{name} is not in the palette')
            return (1, None if acc == base_acc else acc)
        unit = notes[:-1]
        period_number = notes[-1][0] - notes[0][0]
        period_acc = (notes[-1][1] or 0) - (notes[0][1] or 0)
        length = len(unit)
        best = None
        for i, (base, base_acc) in enumerate(unit):
            base_acc = base_acc or 0
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
            residual = abs(acc - (base_acc + q * period_acc))
            if best is None or (residual, degree) < (best[1], best[0]):
                best = (degree, residual)
        if best is not None:
            if strict and best[1]:
                raise SyntaxError(f'{name} is not in the palette')
            return (best[0], None if not best[1] else acc)

        raise SyntaxError(f'{name} is not in the palette')

    # ------------------------------------------------------------ operations

    def map(self, other):
        """`self` seen in `other`: every degree mapped through the palette
        `other`. A bare degree takes the palette's note as the scale spells
        it; an accidental is final — it overrides the palette's, keeping the
        letter. Chords of `self` are kept; `other`'s groups are flat."""
        groups = []
        for group in self.groups:
            notes = []
            for number, acc in group:
                base = other._at((number, None))
                notes.append(base if acc is None else (base[0], acc))
            groups.append(notes)
        return Degrees(groups)

    def unmap(self, other, strict=False):
        """`self`'s notes as (degree, accidental) in the palette `other`."""
        return Degrees([[other._degree_of(number, acc, strict)
                         for number, acc in group] for group in self.groups])

    def compose(self, other):
        """Stack another degree pattern on top of this one (interval addition)."""
        return Degrees(compose_degrees(self.groups, other.groups))

    def transpose(self, interval, up=True):
        """Move every note by a musical interval, measured through the white keys.

        `interval` is a degree, on the same number line as notes: 1 is the
        unison, 2 up a second, 3 up a third, ..., and below the unison 0 is
        down a second, -1 down a third, -2 down a fourth. An accidental adjusts
        the interval in semitones, so '4#' is up a sharp fourth; a bare
        interval is the plain one. `up=False` mirrors the interval around the
        unison, so 2 is down a second.

        The interval keeps its sound, spelled through the white keys: f4 up a
        fourth is Bb4 (a perfect fourth), not B4. A bare note is read as the
        C major spelling — natural — and the result is written out in full,
        with final accidentals.
        """
        if isinstance(interval, str):
            step, acc = _parse_degree(interval.strip())
        elif isinstance(interval, tuple) and len(interval) == 2:
            step, acc = interval
        else:
            raise SyntaxError(f'Illegal interval {interval!r}')

        sign = 1 if up else -1
        move = sign * (step - 1)
        sound = sign * (white_keys._at((step, 0))[0] + (acc or 0))
        groups = []
        for group in self.groups:
            notes = []
            for number, own in group:
                letter = number + move
                value = white_keys._at((number, 0))[0] + (own or 0) + sound
                delta_acc = value - white_keys._at((letter, 0))[0]
                if delta_acc == 0 and acc is None and own is None:
                    delta_acc = None
                notes.append((letter, delta_acc))
            groups.append(notes)
        return Degrees(groups)

    def diatonic(self, interval, up=True):
        """Move every note by whole letter-steps, keeping its accidental.

        `interval` counts letters on the same number line as `transpose`: 1 is
        the unison, 2 up a letter, 0 down a letter, -1 down two letters.
        `up=False` mirrors it, so 2 is down a letter. Only whole steps are
        allowed.
        """
        if isinstance(interval, str):
            text = interval.strip()
            if not re.fullmatch(r'-?\d+', text):
                raise SyntaxError(f'A diatonic interval is whole letters, not {interval!r}')
            step = int(text)
        elif isinstance(interval, int):
            step = interval
        else:
            raise SyntaxError(f'Illegal interval {interval!r}')
        move = step - 1 if up else 1 - step
        return Degrees([[(number + move, acc) for number, acc in group]
                        for group in self.groups])

    def __rshift__(self, other):
        return self.map(other)

    def __lshift__(self, other):
        return self.unmap(other)


# the white keys, whose degrees are semitones (the closing 12 is the period
# marker): the plane `transpose` measures through, and a palette for `>>`/`<<`
white_keys = Degrees(parse_degrees('0n 2n 4n 5n 7n 9n 11n 12n'))
