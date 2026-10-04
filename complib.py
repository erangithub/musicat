import re

LETTERS = 'cdefgab'
NATURAL_PITCH = (0, 2, 4, 5, 7, 9, 11)
ACCIDENTAL_OFFSET = {None: 0, 'bb': -2, 'b': -1, '#': 1, '##': 2}
ACCIDENTAL_NAME = {-2: 'bb', -1: 'b', 0: '', 1: '#', 2: '##'}

class SyntaxError(Exception):
    pass

class NamedNote:
    def __init__(self, name: str):
        match = re.fullmatch('([a-gA-G])(bb|b|#|##)?(-1|[0-7])?', name)
        if not match:
            raise SyntaxError(f'Illegal note name "{name}"')
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
        return f"NamedNote('{self.name}')"


def major_scale(root: str):
    root_note = NamedNote(root)

    start = LETTERS.index(root_note.root.lower())
    root_pitch = (NATURAL_PITCH[start] + ACCIDENTAL_OFFSET[root_note.accidental]) % 12

    note_names = []
    for degree in range(7):
        idx = (start + degree) % 7
        letter = LETTERS[idx]
        pitch = (root_pitch + NATURAL_PITCH[degree]) % 12
        delta = (pitch - NATURAL_PITCH[idx]) % 12
        if delta > 6:
            delta -= 12
        note_names.append(NamedNote(letter + ACCIDENTAL_NAME[delta]))
    return note_names 

def notes(text):
    tokens = text.split()
    for t in tokens:
        nn = NamedNote(t)
        print(nn)

if __name__ == "__main__":
    print('Welcome to complib')
    print(major_scale('d'))

