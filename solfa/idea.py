from .errors import SyntaxError
from .pitches import parse_pitches
from .degrees import (parse_degrees, format_degrees, _parse_degree, white_keys,
                      Degrees)
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

      @       composes:   rhythm @ degrees layers a rhythm onto notes;
                          degrees @ degrees stacks. Either way round.
      *       repeats:    idea * 3 repeats an idea (same level as @).
      +       sequences:  a + b plays a, then b.
      >> <<   resolves:   degrees >> palette selects/resolves through a palette,
                          notes << palette asks for their degrees.

        rhythm('8') @ degrees('1 2 3') @ degrees('0 1 2 3') >> degrees('d4 f a')

    `transpose(interval)` moves every note by a musical interval, counted on the
    same degree number line as notes ('4' is up a fourth, '0' down a second, and
    1 the unison), and `up=False` mirrors it. `diatonic(interval)` moves by whole
    letter-steps instead, keeping each note's accidental.

    `idea[i]` is that one event as a one-event idea, and `idea[a:b]` is a
    shorter idea over that slice of the events — notes and rests in the order
    they play — carrying the durations it actually plays, so the pieces
    recombine with `+`.

    A rhythm loops over the content: with no open group the whole rhythm
    repeats, and '[' marks where the repeating part starts ('4 [8' is a quarter
    and then eighths forever). On its own such a cycling rhythm is infinite.
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
        deg('1 3 5') @ rhy('4 r4 [8'). Long ideas are cut short with
        '…' (those reprs are for reading, not for eval)."""
        parts = []
        if self.content is not None:
            parts.append(f"deg('{format_degrees(self.content.groups, _REPR_GROUPS)}')")
        if self.rhythm is not None:
            parts.append(f"rhy('{format_rhythm(self.rhythm, _REPR_RHYTHM_TOKENS)}')")
        return ' @ '.join(parts) if parts else 'Idea()'

    def _is_empty(self):
        return self.content is None and self.rhythm is None

    # ------------------------------------------------------------ building

    def __mul__(self, other):
        if _is_count(other):
            return self._repeat(other)
        raise SyntaxError(f'Cannot multiply an idea by {other!r}: '
                          'use @ to compose, or an int to repeat')

    def __matmul__(self, other):
        if isinstance(other, Idea):
            return self.compose(other)
        raise SyntaxError(f'Cannot compose an idea with {other!r}: '
                          'use an idea, or * to repeat')

    def __rmatmul__(self, other):
        raise SyntaxError(f'Cannot compose {other!r} with an idea: '
                          'use an idea on both sides')

    def __rmul__(self, other):
        if _is_count(other):
            return self._repeat(other)
        raise SyntaxError(f'Cannot multiply {other!r} by an idea: '
                          'use an int to repeat')

    def compose(self, other):
        """Fill the slots of both ideas into one; degrees with degrees stack,
        and a rhythm on the right replaces one on the left."""
        if self.content is None:
            content = other.content
        elif other.content is None:
            content = self.content
        else:
            content = self.content.compose(other.content)

        if other.rhythm:
            if not other.content:
                rhythm = other.rhythm
            else:
                one_pass = [(rest, duration) for rest, _, duration in other._realize()]
                rhythm = rhythm_from_steps(one_pass)
        else:
            rhythm = self.rhythm
        return Idea(content, rhythm)

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
        return Idea(content, rhythm_from_steps(one_pass))

    def trans(self, interval, up=True):
        """Move every note by a musical interval, measured through the white keys.

        `interval` is a degree, on the same number line as notes: 1 is the
        unison, 2 up a second, 0 down a second, -1 down a third. `up=False`
        mirrors the interval around the unison, so 2 is down a second.
        """
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to transpose')
        return Idea(self.content.transpose(interval, up), self.rhythm)

    def diatrans(self, interval, up=True):
        """Move every note by whole letter-steps, keeping its accidental.

        `interval` counts letters on the same number line as `trans`: 1 is
        the unison, 2 up a letter, 0 down a letter, -1 down two letters.
        `up=False` mirrors it, so 2 is down a letter. Rhythms are kept as they
        are.
        """
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to transpose')
        return Idea(self.content.diatonic(interval, up), self.rhythm)

    # ---------------------------------------------------------- sequencing

    def __add__(self, other):
        """Play this idea, then `other`.

        If both have a rhythm, this idea's rhythm is unrolled over its own
        notes (trailing rests included) and then `other`'s rhythm follows,
        open group and all. If only `other` has a rhythm, this idea's notes
        each take its first duration. If only this idea has one, it simply
        continues over the notes of `other`; a rhythm of only rests has
        nothing to continue over, so it sounds once and `other`'s notes then
        take its first duration. If neither does, none is invented. A rhythm
        that plays only rests carries no notes of its own, so it may be
        concatenated with notes as silence.
        """
        if not isinstance(other, Idea):
            raise SyntaxError(f'Illegal operand {other!r}')
        if self._is_empty():
            return other
        if other._is_empty():
            return self
        if (self.content is None) != (other.content is None):
            # a rhythm that plays only rests carries no notes of its own, so it
            # concatenates as silence; one with sounding steps is ambiguous
            # with composing onto notes (use @ for that)
            silent = other if self.content is not None else self
            if any(not rest for rest, _ in rhythm_steps(silent.rhythm)[0]):
                raise SyntaxError('Cannot concatenate an idea that has notes with a '
                                  'rhythm-only idea; use @ to compose a rhythm onto notes')
            if self.content is None:
                self = Idea(Degrees([]), self.rhythm)
            else:
                other = Idea(Degrees([]), other.rhythm)
        if self.content is None:
            content = None
        else:
            content = Degrees(self.content.groups + other.content.groups)
        return Idea(content, self._joined_rhythm(other))

    def _joined_rhythm(self, other):
        if other.rhythm is None:
            if (self.rhythm and other.content and self.content is not None
                    and not self.content):
                steps, _ = rhythm_steps(self.rhythm)
                if all(rest for rest, _ in steps):
                    # pure silence has no slots to continue over: the rests
                    # sound once and other's notes take the pulse it sets
                    return rhythm_from_steps(
                        steps + [(False, steps[0][1])] * len(other.content))
            return self.rhythm                      # continues over the joined notes
        b_steps, b_loop = rhythm_steps(other.rhythm)
        if b_loop is None:
            b_loop = 0
        if self.rhythm is None:
            a_steps = [(False, b_steps[0][1])] * len(self.content)
        else:
            a_steps = [(rest, duration) for rest, _, duration in self._realize()]
        return rhythm_from_steps(a_steps + b_steps, len(a_steps) + b_loop)

    # ----------------------------------------------------------- mapping

    def __rshift__(self, target):
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to map')
        content = self.content.map(target.content)
        return Idea(content, self.rhythm)

    def __lshift__(self, target):
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to map')
        content = self.content.unmap(target.content)
        return Idea(content, self.rhythm)

    # ------------------------------------------------- inverting, retrograding

    def inv(self, low, high):
        """Chromatically mirror every degree around `low`..`high`; rhythm kept.

        The sound mirrors exactly: over the axis C..G, E ('3') becomes Eb
        ('3b') and over C..C it becomes Ab ('6b'). The mirror resolves to the
        keyboard, so a bare degree or axis point is read as natural and the
        result is written out in full, with final accidentals.
        Accepts degrees as text or (number, accidental) tuples, like `trans`.
        """
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to invert')
        axis = []
        for value in (low, high):
            if isinstance(value, str):
                axis.append(_parse_degree(value.strip()))
            elif isinstance(value, tuple) and len(value) == 2:
                axis.append(value)
            else:
                raise SyntaxError(f'Illegal axis {value!r}')
        (low_step, low_acc), (high_step, high_acc) = axis
        base = ((low_acc or 0) + (high_acc or 0)
                + white_keys._at((low_step, 0))[0]
                + white_keys._at((high_step, 0))[0])
        groups = [[(low_step + high_step - number,
                    base - (acc or 0) - white_keys._at((number, 0))[0]
                    - white_keys._at((low_step + high_step - number, 0))[0])
                   for number, acc in group]
                  for group in self.content.groups]
        return Idea(Degrees(groups), self.rhythm)

    def diainv(self, low, high):
        """Diatonically mirror every degree around `low`..`high`; rhythm kept.

        Each degree's distance from `low` becomes the same distance from
        `high`, so `diainv('1', '5')` turns '1 2 3 4 5' into '5 4 3 2 1'.
        The mirror keeps letters: a bare degree stays bare, and a final
        accidental mirrors its distance from the axis (a sharp becomes a
        flat), the axis points counting as natural. Accepts degrees as text
        or (number, accidental) tuples, like `trans`.
        """
        if self.content is None:
            raise SyntaxError('A rhythm-only idea has nothing to invert')
        axis = []
        for value in (low, high):
            if isinstance(value, str):
                axis.append(_parse_degree(value.strip()))
            elif isinstance(value, tuple) and len(value) == 2:
                axis.append(value)
            else:
                raise SyntaxError(f'Illegal axis {value!r}')
        (low_step, low_acc), (high_step, high_acc) = axis
        groups = [[(low_step + high_step - number,
                    None if acc is None
                    else (low_acc or 0) + (high_acc or 0) - acc)
                   for number, acc in group]
                  for group in self.content.groups]
        return Idea(Degrees(groups), self.rhythm)

    def retro(self, retrograde_degrees=True, retrograde_rhythm=True):
        """Play the idea backwards.

        `retrograde_degrees` reverses the order of the notes,
        `retrograde_rhythm` reverses the sequence of durations and rests,
        and with both the whole idea plays backwards. The rhythm of the
        result is one pass, with no open group.
        """
        play = self._realize()
        steps = [(rest, duration) for rest, _, duration in play]
        notes = [group for _, group, _ in play if group is not None]
        if retrograde_rhythm:
            steps = steps[::-1]
        if retrograde_degrees:
            notes = notes[::-1]
        result = []
        k = 0
        for rest, duration in steps:
            if self.content is None or rest:
                result.append((rest, None, duration))
            else:
                result.append((False, notes[k], duration))
                k += 1
        content = Degrees(notes) if self.content is not None else None
        if self.rhythm is None:
            return Idea(content)
        return Idea(content, rhythm_from_steps(
            [(rest, duration) for rest, _, duration in result]))


    # ------------------------------------------------------------- display

    def __len__(self):
        if not self.content and not self.rhythm:
            return 0
        return len(self._realize())

    def __getitem__(self, key):
        """One event as a one-event idea, or a shorter idea over a slice of events.

        The index counts the events as they play — each note or rest with its
        duration, exactly like `events()` — in every form a list supports:
        negatives, ranges, steps. A slice keeps the durations it actually
        plays, so slicing and recombining with `+` reproduces the original; an
        empty selection is the empty idea. Out-of-range indexes raise
        IndexError. A rhythm-only idea left cycling is infinite: a non-negative
        index and a bounded slice sample it, a slice with no stop keeps it
        cycling, and reading it from the end is an error.
        """
        if not isinstance(key, (int, slice)):
            raise TypeError(f'Idea indices must be integers or slices, not {type(key).__name__}')
        if not self.content and self.rhythm:
            steps, loop_start = rhythm_steps(self.rhythm)
            if loop_start is not None:
                prefix, tail = steps[:loop_start], steps[loop_start:]
                if isinstance(key, int):
                    if key < 0:
                        raise SyntaxError('Cannot read an infinite rhythm from the end')
                    step = prefix[key] if key < loop_start else tail[(key - loop_start) % len(tail)]
                    return Idea(rhythm=rhythm_from_steps([step]))
                start = 0 if key.start is None else key.start
                stop = key.stop
                step = 1 if key.step is None else key.step
                if start < 0 or step < 1 or (stop is not None and stop < 0):
                    raise SyntaxError('Cannot read an infinite rhythm from the end')
                if stop is not None:
                    chosen = []
                    i = start
                    while i < stop:
                        chosen.append(prefix[i] if i < loop_start
                                      else tail[(i - loop_start) % len(tail)])
                        i += step
                    if not chosen:
                        return Idea()
                    return Idea(rhythm=rhythm_from_steps(chosen))
                if step != 1:
                    raise SyntaxError('Cannot read an infinite rhythm with a step and no stop')
                if start < loop_start:
                    new_steps = prefix[start:] + tail
                    return Idea(rhythm=rhythm_from_steps(new_steps, loop_start - start))
                offset = (start - loop_start) % len(tail)
                return Idea(rhythm=rhythm_from_steps(tail[offset:] + tail[:offset], 0))
        play = [] if not self.content and not self.rhythm else self._realize()
        picked = play[key]
        if isinstance(key, int):
            picked = [picked]
        if not picked:
            return Idea()
        groups = [group for _, group, _ in picked if group is not None]
        # a content idea stays a content idea even when the slice lands only on
        # rests, so its pieces still join with + (empty Degrees, not None)
        content = Degrees(groups) if self.content is not None or groups else None
        if self.rhythm is None:
            return Idea(content)
        return Idea(content, rhythm_from_steps([(rest, duration)
                                                for rest, _, duration in picked]))

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
        rest that only begins the next pass of the loop is not. A rhythm-only
        idea left cycling has no last event to stop at: it is infinite.
        """
        if self.rhythm:
            steps, loop_start = rhythm_steps(self.rhythm)
        else:
            steps, loop_start = [(False, WHOLE)], None
        groups = self.content.groups if self.content is not None else None
        if not groups:
            if loop_start is not None:
                raise SyntaxError('infinite rhythm; pair it with degrees or slice it')
            return [(rest, None, duration) for rest, duration in steps]
        sounding = sum(1 for rest, _ in steps if not rest)
        start = 0 if loop_start is None else loop_start
        if len(groups) > sounding and all(rest for rest, _ in steps[start:]):
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
                k = start
        while k < len(steps) and steps[k][0]:
            result.append((True, None, steps[k][1]))
            k += 1
        return result

    def events(self):
        """[(group, duration)] ready for rendering; a rest has an empty group."""
        return [([] if group is None else group, duration)
                for _, group, duration in self._realize()]


def pit(text):
    return Idea(parse_pitches(text))

def deg(text):
    return Idea(Degrees(parse_degrees(text)))

def rhy(text):
    return Idea(rhythm=parse_rhythm(text))
