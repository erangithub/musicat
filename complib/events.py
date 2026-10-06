from .errors import SyntaxError
from .pitches import Pitch
from .rhythm import QUARTER


class Event:
    def __init__(self, pitches=None, duration=QUARTER):
        parsed = []
        for pitch in (pitches or []):
            if isinstance(pitch, str):
                pitch = Pitch(pitch)
            elif not isinstance(pitch, Pitch):
                raise SyntaxError(f'Illegal pitch {pitch!r}')
            parsed.append(pitch)
        self.pitches = parsed
        self.duration = duration

    def midipitches(self):
        return [p.midipitch() for p in self.pitches]

    def __eq__(self, other):
        if not isinstance(other, Event):
            return NotImplemented
        return (type(self) is type(other) and self.pitches == other.pitches
                and self.duration == other.duration)

    def __hash__(self):
        return hash((type(self), tuple(self.pitches), self.duration))

    def __str__(self):
        body = ' '.join(str(p) for p in self.pitches)
        return f'{body} {self.duration}' if body else str(self.duration)

    def __repr__(self):
        body = ' '.join(str(p) for p in self.pitches)
        pitches = f"'{body}', " if body else ''
        return f"{type(self).__name__}({pitches}{self.duration})"


class Note(Event):
    def __init__(self, pitch, duration=QUARTER):
        super().__init__([pitch], duration)


class Chord(Event):
    def __init__(self, pitches=None, duration=QUARTER):
        super().__init__(pitches, duration)
        voiced = []
        running = None
        for pitch in self.pitches:
            if pitch.octave is not None:
                voiced.append(pitch)
                running = pitch.midipitch()
                continue
            base = pitch.midipitch()
            octave = 4 if running is None else (running - base) // 12
            if not -1 <= octave <= 7:
                raise SyntaxError(f'Chord reaches past the octave range at {pitch}')
            voiced.append(Pitch(f'{pitch.root}{pitch.accidental or ""}{octave}'))
            running = base + 12 * (octave + 1)
        self.pitches = voiced


class Rest(Event):
    def __init__(self, duration=QUARTER):
        super().__init__(None, duration)

    def __str__(self):
        return f'r {self.duration}'


Sequence = list[Event]


def combine(pitches, rhythm):
    if not rhythm:
        raise SyntaxError('Empty rhythm')
    events = []
    for i, group in enumerate(pitches):
        group = group if isinstance(group, (list, tuple)) else [group]
        duration = rhythm[i % len(rhythm)]
        if not group:
            events.append(Rest(duration))
        elif len(group) == 1:
            events.append(Note(group[0], duration))
        else:
            events.append(Chord(group, duration))
    return events
