import re

LETTERS = 'cdefgab'
NATURAL_PITCH = (0, 2, 4, 5, 7, 9, 11)
ACCIDENTAL_OFFSET = {None: 0, 'bb': -2, 'b': -1, '#': 1, '##': 2}
ACCIDENTAL_NAME = {-2: 'bb', -1: 'b', 0: '', 1: '#', 2: '##'}

class SyntaxError(Exception):
    pass

class Pitch:
    def __init__(self, name: str):
        match = re.fullmatch('([a-gA-G])(bb|b|#|##)?(-1|[0-7])?', name)
        if not match:
            raise SyntaxError(f'Illegal pitch name "{name}"')
        self.name = name
        self.root = match.group(1)
        self.accidental = match.group(2)
        self.octave = int(match.group(3)) if match.group(3) else None

    def midipitch(self):
        idx = LETTERS.index(self.root.lower())
        base = NATURAL_PITCH[idx]
        if self.octave is not None:
            base += 12 * (self.octave+1)
        base += ACCIDENTAL_OFFSET[self.accidental]

        return base

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Pitch('{self.name}')"


class Duration:
    def __str__(self):
        return '1/4'

    def __repr__(self):
        return 'Duration()'


class Note:
    def __init__(self, pitch, duration=None):
        self.pitch = Pitch(pitch) if isinstance(pitch, str) else pitch
        self.duration = Duration() if duration is None else duration

    def midipitch(self):
        return self.pitch.midipitch()

    def __str__(self):
        return f'{self.pitch} {self.duration}'

    def __repr__(self):
        return f"Note('{self.pitch}', {self.duration})"


def major_scale(root: str):
    root_pitch = Pitch(root)

    start = LETTERS.index(root_pitch.root.lower())
    root_pc = (NATURAL_PITCH[start] + ACCIDENTAL_OFFSET[root_pitch.accidental]) % 12

    pitches = []
    for degree in range(7):
        idx = (start + degree) % 7
        letter = LETTERS[idx]
        pitch_pc = (root_pc + NATURAL_PITCH[degree]) % 12
        delta = (pitch_pc - NATURAL_PITCH[idx]) % 12
        if delta > 6:
            delta -= 12
        pitches.append(Pitch(letter + ACCIDENTAL_NAME[delta]))
    return pitches 

def to_pitches(text):
    tokens = text.split()
    return map(Pitch, tokens)


def show():
    import verovio
    toolkit = verovio.toolkit()
    toolkit.setOptions({'adjustPageHeight': True, 'scale': 40})
    if not toolkit.loadData(open('mock/probe.musicxml').read()):
        raise SyntaxError('Illegal MusicXML')
    svg = toolkit.renderToSVG(1)
    try:
        from IPython.display import SVG, display
        display(SVG(svg))
    except ImportError:
        pass

if __name__ == "__main__":
    print('Welcome to complib')
    print(major_scale('d'))

