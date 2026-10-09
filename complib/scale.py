from .pitches import Pitch, to_pitches

def _flatten(xss):
    return [x for xs in xss for x in xs]

class Scale:
    def __init__(self, root_str : str, pitches_str: str):
        self._pitches = _flatten(to_pitches(pitches_str))
        self._len = len(self._pitches)
        self.root = Pitch(root_str)

    def at(self, degree : int, acc_offset : int = 0):
        octave = (degree - 1) // self._len
        idx = degree % self._len
        result = self.root + self._pitches[idx-1] + Pitch('c', octave)
        result.acc += acc_offset 
        return result

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
        return f"Scale('{self.root}', '{orig_pitches}')"

def major_scale(root_str):
    return Scale(root_str, 'c d e f g a b')
