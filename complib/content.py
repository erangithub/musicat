"""The two kinds of musical content an Idea can hold.

Pitches and Degrees are each a list of groups (a group is one note or a chord).
They are the two ends of `against`: degrees seen through a palette give pitches,
and pitches seen through a palette give degrees.
"""
from .degrees import stack_degrees
from .errors import SyntaxError
from .palette import Palette


def _check_palette(palette):
    if not isinstance(palette, Palette):
        raise SyntaxError(f'Cannot resolve against {palette!r}: expected a Palette')


class _Content:
    kind = ''

    def __init__(self, groups):
        self.groups = groups

    def __len__(self):
        return len(self.groups)

    def __iter__(self):
        return iter(self.groups)

    def __getitem__(self, index):
        return self.groups[index]

    def __eq__(self, other):
        return type(other) is type(self) and self.groups == other.groups

    def __repr__(self):
        return f'{type(self).__name__}({self.groups!r})'


class Pitches(_Content):
    """Concrete pitches: a list of groups of Pitch."""
    kind = 'pitches'

    def against(self, palette, strict=False):
        """These pitches seen as degrees of `palette`.

        Chromatic by default: a note outside the palette becomes the nearest
        degree plus an accidental (c# against C major is 1#). With strict=True
        a note outside the palette raises instead.
        """
        _check_palette(palette)
        return Degrees([[palette.degree_of(pitch, strict) for pitch in group]
                        for group in self.groups])


class Degrees(_Content):
    """Scale degrees: a list of groups of (degree, accidental)."""
    kind = 'degrees'

    def stack(self, other):
        """Stack another degree pattern on top of this one (interval addition)."""
        return Degrees(stack_degrees(self.groups, other.groups))

    def against(self, palette, strict=False):
        """These degrees resolved to pitches in `palette`. (`strict` is accepted
        for symmetry with Pitches.against; this direction always succeeds.)"""
        _check_palette(palette)
        return Pitches([[palette.at(number, acc) for number, acc in group]
                        for group in self.groups])
