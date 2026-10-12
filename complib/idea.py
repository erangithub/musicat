from .errors import SyntaxError
from .pitches import parse_pitches
from .degrees import parse_degrees
from .rhythm import parse_rhythm, REST_MARKER, WHOLE
from .palette import Palette
from .content import Pitches, Degrees


class Idea:
    """A musical idea: optional content (Pitches or Degrees) plus optional rhythm.

    `+` fills the two slots (each can be filled once), `*` stacks degree
    patterns, and `>>` pours the idea through a palette: degrees become
    pitches, pitches become degrees.

        rhythm('/8') + degrees('1 2 3') * degrees('0 1 2 3') >> Palette('d4 f a')

    `+` and `*` bind tighter than `>>`, so the whole left side is built first.
    """

    def __init__(self, content=None, rhythm=None):
        if content is not None and not isinstance(content, (Pitches, Degrees)):
            raise SyntaxError(f'Illegal content {content!r}')
        self.content = content
        self.rhythm = rhythm

    @property
    def pitches(self):
        return self.content.groups if isinstance(self.content, Pitches) else None

    @property
    def degrees(self):
        return self.content.groups if isinstance(self.content, Degrees) else None

    def __eq__(self, other):
        return (isinstance(other, Idea)
                and self.content == other.content
                and self.rhythm == other.rhythm)

    def __repr__(self):
        fields = ', '.join(
            f'{name}={value!r}' for name in ('pitches', 'degrees', 'rhythm')
            if (value := getattr(self, name)) is not None)
        return f'Idea({fields})'

    def __add__(self, other):
        if not isinstance(other, Idea):
            raise SyntaxError(f'Illegal operand {other!r}')
        if self.content is not None and other.content is not None:
            if type(self.content) is type(other.content):
                raise SyntaxError(f'Cannot combine ideas that share {self.content.kind}')
            raise SyntaxError('Idea cannot have both pitches and degrees')
        if self.rhythm is not None and other.rhythm is not None:
            raise SyntaxError('Cannot combine ideas that share rhythm')
        return Idea(
            content=self.content if self.content is not None else other.content,
            rhythm=self.rhythm if self.rhythm is not None else other.rhythm)

    def __mul__(self, other):
        if not isinstance(other, Idea):
            raise SyntaxError(f'Illegal operand {other!r}')
        if self.rhythm is not None and other.rhythm is not None:
            raise SyntaxError('Cannot combine ideas that share rhythm')
        if not isinstance(self.content, Degrees):
            raise SyntaxError("Cannot stack ideas that don't have degrees")
        if not isinstance(other.content, Degrees):
            raise SyntaxError("Cannot stack ideas that don't have degrees")
        return Idea(
            content=self.content.stack(other.content),
            rhythm=self.rhythm if self.rhythm is not None else other.rhythm)

    def against(self, palette, strict=False):
        """Pour this idea through `palette`: degrees become pitches and pitches
        become degrees. The rhythm is carried along unchanged. `strict` only
        matters for pitches -> degrees (see Palette.degree_of)."""
        if not isinstance(palette, Palette):
            raise SyntaxError(f'Cannot resolve against {palette!r}: expected a Palette')
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to resolve against a palette')
        return Idea(content=self.content.against(palette, strict), rhythm=self.rhythm)

    def __rshift__(self, palette):
        return self.against(palette)

    def as_pitches(self, palette):
        if not isinstance(self.content, Degrees):
            raise SyntaxError('An idea without degrees has no pitches to resolve')
        return self.against(palette)

    def as_degrees(self, palette, strict=False):
        if not isinstance(self.content, Pitches):
            raise SyntaxError('An idea without pitches has no degrees to analyze')
        return self.against(palette, strict)

    def __len__(self):
        if self.content is not None:
            return len(self.content)
        elif self.rhythm is not None:
            return len(self.rhythm)
        else:
            return 0

    def show(self, time='4/4'):
        from . import Part
        Part(self).show(time)

    def _repr_svg_(self):
        return self.show()

    def events(self):
        steps = _rhythm_steps(self.rhythm or [WHOLE])
        groups = self.pitches
        if not groups:
            return [([], duration) for _, duration in steps]
        if all(rest for rest, _ in steps):
            raise SyntaxError('Rhythm has no sounding notes to put pitches on')
        result = []
        i = 0
        k = 0
        while i < len(groups):
            rest, duration = steps[k % len(steps)]
            k += 1
            if rest:
                result.append(([], duration))
            else:
                result.append((groups[i], duration))
                i += 1
        return result


def _rhythm_steps(rhythm):
    """Group a rhythm list into (is_rest, duration) steps."""
    steps = []
    i = 0
    while i < len(rhythm):
        if rhythm[i] == REST_MARKER:
            if i + 1 >= len(rhythm):
                raise SyntaxError('Rest marker without a duration')
            steps.append((True, rhythm[i + 1]))
            i += 2
        else:
            steps.append((False, rhythm[i]))
            i += 1
    return steps


def pitches(text):
    return Idea(Pitches(parse_pitches(text)))

def degrees(text):
    return Idea(Degrees(parse_degrees(text)))

def rhythm(text):
    return Idea(rhythm=parse_rhythm(text))
