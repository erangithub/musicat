from .errors import SyntaxError
from .pitches import Pitch, parse_pitches

def _flatten(xss):
    return [x for xs in xss for x in xs]

class Palette:
    def __init__(self, pitches_str: str, root_str : str = "c0"):
        self._pitches = _flatten(parse_pitches(pitches_str))
        self._len = len(self._pitches)
        if not self._len:
            raise SyntaxError('Empty palette')
        self.root = Pitch(root_str)

    def at(self, degree : int, acc_offset : int = 0):
        octave = (degree - 1) // self._len
        idx = degree % self._len
        result = self.root + self._pitches[idx-1] + Pitch('c', octave)
        result.acc += acc_offset 
        return result

    def degree_of(self, pitch, strict=False):
        """Inverse of `at`: the (degree, accidental) that `at` maps to `pitch`.

        Spelling is preserved: a degree is chosen whose letter name matches the
        pitch (db is 2b and c# is 1# in C major, never the same thing). If the
        palette has several such degrees the one needing the smallest accidental
        wins, then the lowest degree.

        If no degree shares the pitch's letter (f against a pentatonic palette)
        the nearest degree by sound is used, ties going to the lower degree
        with a raising accidental. That round-trips the sound but not the
        spelling (f may come back as e#).

        With strict=True the pitch must be exactly a palette note, otherwise
        SyntaxError is raised.
        """
        best = None
        for j, base in enumerate(self._pitches):
            diff = pitch.idx - self.root.idx - base.idx
            if diff % 7:
                continue
            degree = diff // 7 * self._len + j + 1
            acc = pitch.acc - self.at(degree).acc
            if best is None or (abs(acc), degree) < (abs(best[1]), best[0]):
                best = (degree, acc)
        if best is not None:
            if strict and best[1]:
                raise SyntaxError(f'{pitch} is not in the palette')
            return best
        if strict:
            raise SyntaxError(f'{pitch} is not in the palette')
        target = pitch.midipitch()
        nearest = None
        for j, base in enumerate(self._pitches):
            octave = (pitch.idx - self.root.idx - base.idx) // 7
            for n in (octave, octave + 1):
                degree = n * self._len + j + 1
                key = (abs(target - self.at(degree).midipitch()), degree)
                if nearest is None or key < nearest:
                    nearest = key
        degree = nearest[1]
        return degree, target - self.at(degree).midipitch()

    def __len__(self):
        return self._len

    def __iter__(self):
        return (self.at(degree) for degree in range(1, self._len + 1))

    def __getitem__(self, degree):
        if isinstance(degree, slice):
            start = degree.start if degree.start is not None else 1
            stop = degree.stop if degree.stop is not None else self._len + 1
            step = degree.step or 1
            return [self.at(index) for index in range(start, stop, step)]
        return self.at(degree)

    def __str__(self):
        return ' '.join(str(pitch) for pitch in self)

    def __repr__(self):
        orig_pitches = ' '.join(str(pitch) for pitch in self._pitches)
        return f"Palette('{orig_pitches}', '{self.root}')"

def major_scale(root_str):
    return Palette('c0 d e f g a b', root_str)

def minor_scale(root_str):
    return Palette('c0 d eb f g ab bb', root_str)
