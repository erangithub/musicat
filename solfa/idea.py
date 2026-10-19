from fractions import Fraction

from .errors import SyntaxError
from .pitches import parse_pitches
from .degrees import (parse_degrees, format_degrees, _parse_degree, white_keys,
                      Degrees)
from .rhythm import (parse_rhythm, format_rhythm, OpenMarker, CloseMarker,
                     RestMarker, WHOLE)


# how much of an idea its repr shows before truncating with '…'
_REPR_GROUPS = 16
_REPR_RHYTHM_TOKENS = 16


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _rhythm_from_events(events, loop=None):
    """Rebuild a rhythm from realized events.

    Each event is (is_rest, group, nominal, tuplets); the group is not used, and
    a tuplet is (k, j, start) — its ratio and the step it opened at, so that two
    neighbouring tuplets of the same ratio stay distinct groups. The written
    (relative) durations come back as they were, wrapped in the tuplet markers
    they sit in. `loop`, an index into `events`, marks where the cycling tail
    begins and gets a bare open marker.
    """
    rhythm = []
    open_tuplets = ()
    for index, (is_rest, _, nominal, tuplets) in enumerate(events):
        if index == loop:
            rhythm.append(OpenMarker())
        tuplets = tuplets or ()
        common = 0
        while (common < len(open_tuplets) and common < len(tuplets)
               and open_tuplets[common] == tuplets[common]):
            common += 1
        rhythm.extend([CloseMarker()] * (len(open_tuplets) - common))
        rhythm.extend([OpenMarker(k, j) for k, j, _ in tuplets[common:]])
        open_tuplets = tuplets
        rhythm.append(RestMarker(nominal) if is_rest else nominal)
    rhythm.extend([CloseMarker()] * len(open_tuplets))
    return rhythm



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
                rhythm = _rhythm_from_events(other._realize())
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
        return Idea(content, _rhythm_from_events(self._realize()))

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
            steps = []
            stack = []
            for item in silent.rhythm or []:
                if isinstance(item, OpenMarker):
                    stack.append(item)
                elif isinstance(item, CloseMarker):
                    if stack:
                        stack.pop()
                elif isinstance(item, RestMarker):
                    steps.append(True)
                else:
                    steps.append(False)
            if any(not rest for rest in steps):
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
                steps = []
                stack = []
                for item in self.rhythm:
                    if isinstance(item, OpenMarker):
                        stack.append(item)
                    elif isinstance(item, CloseMarker):
                        if stack:
                            stack.pop()
                    elif isinstance(item, RestMarker):
                        steps.append((True, item.duration,
                                      tuple((m.k, m.j) for m in stack
                                            if m.k is not None)))
                    else:
                        steps.append((False, item,
                                      tuple((m.k, m.j) for m in stack
                                            if m.k is not None)))
                if all(rest for rest, _, _ in steps):
                    # pure silence has no slots to continue over: the rests
                    # sound once and other's notes take the pulse it sets
                    pulse = steps[0]
                    rhythm = list(self.rhythm)
                    for _ in range(len(other.content)):
                        rhythm.extend([OpenMarker(k, j) for k, j in pulse[2]])
                        rhythm.append(pulse[1])
                        rhythm.extend([CloseMarker()] * len(pulse[2]))
                    return rhythm
            return self.rhythm                      # continues over the joined notes
        rhythm = _rhythm_from_events(self._realize() if self.rhythm else [])
        if self.rhythm is None:
            stack = []
            first = (False, WHOLE, ())
            for item in other.rhythm:
                if isinstance(item, OpenMarker):
                    stack.append(item)
                elif isinstance(item, CloseMarker):
                    if stack:
                        stack.pop()
                else:
                    rest = isinstance(item, RestMarker)
                    first = (rest, item.duration if rest else item,
                             tuple((m.k, m.j) for m in stack
                                   if m.k is not None))
                    break
            for _ in range(len(self.content)):
                rhythm.extend([OpenMarker(k, j) for k, j in first[2]])
                rhythm.append(first[1])
                rhythm.extend([CloseMarker()] * len(first[2]))
        # other's own rhythm follows, open group and all; when it has none we
        # still mark where it repeats
        depth = 0
        for item in other.rhythm:
            if isinstance(item, OpenMarker):
                depth += 1
            elif isinstance(item, CloseMarker):
                depth -= 1
        if depth == 0:
            rhythm.append(OpenMarker())
        rhythm.extend(other.rhythm)
        return rhythm

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
        events = play[::-1] if retrograde_rhythm else play
        notes = [group for _, group, _, _ in play if group is not None]
        if retrograde_degrees:
            notes = notes[::-1]
        result = []
        k = 0
        for rest, group, nominal, tuplets in events:
            if self.content is None or rest:
                result.append((rest, None, nominal, tuplets))
            else:
                result.append((False, notes[k], nominal, tuplets))
                k += 1
        content = Degrees(notes) if self.content is not None else None
        if self.rhythm is None:
            return Idea(content)
        return Idea(content, _rhythm_from_events(result))


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
            steps = []
            stack = []
            for item in self.rhythm:
                if isinstance(item, OpenMarker):
                    stack.append([item, len(steps)])
                elif isinstance(item, CloseMarker):
                    if stack:
                        stack.pop()
                else:
                    rest = isinstance(item, RestMarker)
                    nominal = item.duration if rest else item
                    steps.append((rest, None, nominal,
                                  tuple((m[0].k, m[0].j, m[1]) for m in stack
                                        if m[0].k is not None)))
            loop = stack[-1][1] if stack else None
            if loop is not None:
                prefix, tail = steps[:loop], steps[loop:]
                if isinstance(key, int):
                    if key < 0:
                        raise SyntaxError('Cannot read an infinite rhythm from the end')
                    chosen = [prefix[key] if key < loop
                              else tail[(key - loop) % len(tail)]]
                    loop_at = None
                else:
                    start = 0 if key.start is None else key.start
                    stop = key.stop
                    step = 1 if key.step is None else key.step
                    if start < 0 or step < 1 or (stop is not None and stop < 0):
                        raise SyntaxError('Cannot read an infinite rhythm from the end')
                    if stop is not None:
                        chosen = []
                        i = start
                        while i < stop:
                            chosen.append(prefix[i] if i < loop
                                          else tail[(i - loop) % len(tail)])
                            i += step
                        loop_at = None
                    elif step != 1:
                        raise SyntaxError('Cannot read an infinite rhythm with a step and no stop')
                    elif start < loop:
                        chosen = prefix[start:] + tail
                        loop_at = loop - start
                    else:
                        offset = (start - loop) % len(tail)
                        chosen = tail[offset:] + tail[:offset]
                        loop_at = 0
                if not chosen:
                    return Idea()
                return Idea(rhythm=_rhythm_from_events(chosen, loop_at))
        play = [] if not self.content and not self.rhythm else self._realize()
        picked = play[key]
        if isinstance(key, int):
            picked = [picked]
        if not picked:
            return Idea()
        groups = [group for _, group, _, _ in picked if group is not None]
        # a content idea stays a content idea even when the slice lands only on
        # rests, so its pieces still join with + (empty Degrees, not None)
        content = Degrees(groups) if self.content is not None or groups else None
        if self.rhythm is None:
            return Idea(content)
        return Idea(content, _rhythm_from_events(picked))

    def show(self, time='4/4'):
        from . import Part
        Part(self).show(time)

    def _repr_svg_(self):
        return self.show()

    # -------------------------------------------------------------- events

    def _realize(self):
        """Unroll the rhythm over the content, once.

        Returns [(is_rest, group, nominal, tuplets)], where group is None for
        rests and for the steps of a rhythm-only idea, and tuplets lists the
        enclosing (k, j) ratios outermost first. Durations are the written
        (relative) values; `events()` scales them by the tuplets into actual
        time. Every note of the content is used exactly once. Rests written
        after the last note, in the same pass of the rhythm, are kept
        ('4 4 r2' over two notes ends with the half rest); a rest that only
        begins the next pass of the loop is not. A rhythm-only idea left
        cycling has no last event to stop at: it is infinite.
        """
        if self.rhythm:
            steps = []
            stack = []
            for item in self.rhythm:
                if isinstance(item, OpenMarker):
                    stack.append([item, len(steps)])
                elif isinstance(item, CloseMarker):
                    if stack:
                        stack.pop()
                else:
                    rest = isinstance(item, RestMarker)
                    nominal = item.duration if rest else item
                    steps.append((rest, nominal,
                                  tuple((m[0].k, m[0].j, m[1]) for m in stack
                                        if m[0].k is not None)))
            loop = stack[-1][1] if stack else None
        else:
            steps = [(False, WHOLE, ())]
            loop = None
        groups = self.content.groups if self.content is not None else None
        if not groups:
            if loop is not None:
                raise SyntaxError('infinite rhythm; pair it with degrees or slice it')
            return [(rest, None, nominal, tuplets)
                    for rest, nominal, tuplets in steps]
        sounding = sum(1 for rest, _, _ in steps if not rest)
        start = 0 if loop is None else loop
        if len(groups) > sounding and all(rest for rest, _, _ in steps[start:]):
            raise SyntaxError('The looping part of the rhythm has no sounding '
                              'notes to put the content on')
        result = []
        used = 0
        k = 0
        while used < len(groups):
            rest, nominal, tuplets = steps[k]
            if rest:
                result.append((True, None, nominal, tuplets))
            else:
                result.append((False, groups[used], nominal, tuplets))
                used += 1
            k += 1
            if k == len(steps) and used < len(groups):
                k = start
        while k < len(steps) and steps[k][0]:
            result.append((True, None, steps[k][1], steps[k][2]))
            k += 1
        return result

    def events(self):
        """[(group, duration)] ready for rendering; a rest has an empty group."""
        out = []
        for _, group, nominal, tuplets in self._realize():
            actual = nominal
            for k, j, _ in (tuplets or ()):
                actual = actual * Fraction(j, k)
            out.append(([] if group is None else group, actual))
        return out


def pit(text):
    return Idea(parse_pitches(text))

def deg(text):
    return Idea(Degrees(parse_degrees(text)))

def rhy(text):
    return Idea(rhythm=parse_rhythm(text))
