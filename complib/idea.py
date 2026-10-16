from .errors import SyntaxError
from .pitches import parse_pitches
from .degrees import parse_degrees, format_degrees, Degrees
from .rhythm import (parse_rhythm, format_rhythm, rhythm_steps,
                     rhythm_from_steps, WHOLE)


# how much of an idea its repr shows before truncating with '…'
_REPR_GROUPS = 16
_REPR_RHYTHM_TOKENS = 16


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Idea:
    """A musical idea: optional content (Degrees) plus optional rhythm.

    Three levels of operator, tightest first:

      *       builds:     rhythm * degrees layers a rhythm onto notes,
                          degrees * degrees stacks, idea * 3 repeats.
      +       sequences:  a + b plays a, then b.
      >> <<   resolves:   degrees >> palette selects/resolves through a palette,
                          notes << palette asks for their degrees.

        rhythm('8') * degrees('1 2 3') * degrees('0 1 2 3') >> degrees('d4 f a')

    `transpose(interval, palette)` moves every note by a degree, or a string like
    '4#' / '-4#', through a plane (the white keys by default, or another palette).

    A rhythm loops over the content: with no loop marker the whole rhythm
    repeats, and '|:' marks where the repeating part starts ('4 |: 8' is a
    quarter and then eighths forever).
    """

    def __init__(self, content=None, rhythm=None):
        if content is not None and not isinstance(content, Degrees):
            raise SyntaxError(f'Illegal content {content!r}')
        self.content = content
        self.rhythm = rhythm if rhythm else None

    def __eq__(self, other):
        return (isinstance(other, Idea)
                and self.content == other.content
                and self.rhythm == other.rhythm)

    def __repr__(self):
        """The expression that builds this idea, e.g.
        degrees('1 3 5') * rhythm('4 r4 |: 8'). Long ideas are cut short with
        '…' (those reprs are for reading, not for eval)."""
        parts = []
        if self.content is not None:
            parts.append(f"degrees('{format_degrees(self.content.groups, _REPR_GROUPS)}')")
        if self.rhythm is not None:
            parts.append(f"rhythm('{format_rhythm(self.rhythm, _REPR_RHYTHM_TOKENS)}')")
        return ' * '.join(parts) if parts else 'Idea()'

    def _is_empty(self):
        return self.content is None and self.rhythm is None

    # ------------------------------------------------------------ building

    def __mul__(self, other):
        if isinstance(other, Idea):
            return self._layer(other)
        if _is_count(other):
            return self._repeat(other)
        raise SyntaxError(f'Cannot multiply an idea by {other!r}: '
                          'use another idea to layer, or an int to repeat')

    def __rmul__(self, other):
        if _is_count(other):
            return self._repeat(other)
        raise SyntaxError(f'Cannot multiply {other!r} by an idea: '
                          'use an int to repeat')

    def _layer(self, other):
        """Fill the slots of both ideas into one; degrees with degrees stack."""
        if self.rhythm is not None and other.rhythm is not None:
            raise SyntaxError('Cannot combine ideas that share rhythm')
        if self.content is None:
            content = other.content
        elif other.content is None:
            content = self.content
        else:
            content = self.content.stack(other.content)

        if self.rhythm:
            one_pass = [(rest, duration) for rest, _, duration in self._realize()]
            return Idea(content, rhythm_from_steps(one_pass, 0))
        else:
            return Idea(content, other.rhythm)

    def _repeat(self, count):
        """Play this idea `count` times.

        The rhythm is unrolled once over one pass of the notes and then simply
        loops over the repeated notes, so it stays as long as the idea itself
        however many times it repeats.
        """
        if count < 1:
            raise SyntaxError(f'Repeat count must be a positive integer, not {count}')
        if count == 1:
            return self
        if self.content is None or not self.content.groups:
            result = self                       # rhythm only: nothing to loop over
            for _ in range(count - 1):
                result = result + self
            return result
        content = Degrees(self.content.groups * count)
        if self.rhythm is None:
            return Idea(content)
        one_pass = [(rest, duration) for rest, _, duration in self._realize()]
        return Idea(content, rhythm_from_steps(one_pass, 0))

    def transpose(self, interval, palette=None):
        """Move every note by a degree `interval` through a plane.

        `interval` is a (number, accidental) degree, a one-note Degrees, or a
        string in the degrees syntax ('4#' is up a sharp fourth, '-4#' down
        one). The plane is the white keys by default; pass another palette (a
        Degrees) to measure in a different plane. Rhythms are kept as they are.
        """
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to transpose')
        return Idea(self.content.transpose(interval, palette), self.rhythm)

    # ---------------------------------------------------------- sequencing

    def __add__(self, other):
        """Play this idea, then `other`.

        If both have a rhythm, this idea's rhythm is unrolled over its own
        notes (trailing rests included) and then `other`'s rhythm follows,
        loop marker and all. If only `other` has a rhythm, this idea's notes
        each take its first duration. If only this idea has one, it simply
        continues over the notes of `other`. If neither does, none is invented.
        """
        if not isinstance(other, Idea):
            raise SyntaxError(f'Illegal operand {other!r}')
        if self._is_empty():
            return other
        if other._is_empty():
            return self
        if (self.content is None) != (other.content is None):
            raise SyntaxError('Cannot concatenate an idea that has notes with a '
                              'rhythm-only idea; use * to layer a rhythm onto notes')
        if self.content is None:
            content = None
        else:
            content = Degrees(self.content.groups + other.content.groups)
        return Idea(content, self._joined_rhythm(other))

    def _joined_rhythm(self, other):
        if other.rhythm is None:
            return self.rhythm                      # continues over the joined notes
        b_steps, b_loop = rhythm_steps(other.rhythm)
        if self.rhythm is None:
            a_steps = [(False, b_steps[0][1])] * len(self.content)
        else:
            a_steps = [(rest, duration) for rest, _, duration in self._realize()]
        return rhythm_from_steps(a_steps + b_steps, len(a_steps) + b_loop)

    # ----------------------------------------------------------- resolving

    def __rshift__(self, palette):
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to resolve')
        content = self.content.compose(palette.content if isinstance(palette, Idea)
                                       else palette)
        return Idea(content, self.rhythm)

    def __lshift__(self, palette):
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to resolve')
        content = self.content.decompose(palette.content if isinstance(palette, Idea)
                                         else palette)
        return Idea(content, self.rhythm)

    # ------------------------------------------------------------- display

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

    # -------------------------------------------------------------- events

    def _realize(self):
        """Unroll the rhythm over the content, once.

        Returns [(is_rest, group, duration)], where group is None for rests and
        for the steps of a rhythm-only idea. Every note of the content is used
        exactly once. Rests written after the last note, in the same pass of the
        rhythm, are kept ('4 4 r2' over two notes ends with the half rest); a
        rest that only begins the next pass of the loop is not.
        """
        if self.rhythm:
            steps, loop_start = rhythm_steps(self.rhythm)
        else:
            steps, loop_start = [(False, WHOLE)], 0
        groups = self.content.groups if self.content is not None else None
        if not groups:
            return [(rest, None, duration) for rest, duration in steps]
        if all(rest for rest, _ in steps[loop_start:]):
            raise SyntaxError('The looping part of the rhythm has no sounding '
                              'notes to put the content on')
        result = []
        used = 0
        k = 0
        while used < len(groups):
            rest, duration = steps[k]
            if rest:
                result.append((True, None, duration))
            else:
                result.append((False, groups[used], duration))
                used += 1
            k += 1
            if k == len(steps) and used < len(groups):
                k = loop_start
        while k < len(steps) and steps[k][0]:
            result.append((True, None, steps[k][1]))
            k += 1
        return result

    def events(self):
        """[(group, duration)] ready for rendering; a rest has an empty group."""
        return [([] if group is None else group, duration)
                for _, group, duration in self._realize()]


def pitches(text):
    return Idea(parse_pitches(text))

def degrees(text):
    return Idea(Degrees(parse_degrees(text)))

def rhythm(text):
    return Idea(rhythm=parse_rhythm(text))
