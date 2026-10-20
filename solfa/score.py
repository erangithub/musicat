import re

from .errors import SyntaxError


class Part:
    def __init__(self, idea, name='Music'):
        self.idea = idea
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Part('{self.name}', {len(self.idea)} events)"

    def show(self, time='4/4'):
        from . import render_verovio
        render_verovio.show_score(Score([self], time))

    def play(self, time='4/4'):
        from . import playback
        playback.play(Score([self], time))


class Score:
    def __init__(self, parts, time='4/4'):
        if not parts:
            raise SyntaxError('Empty score')
        for part in parts:
            if not isinstance(part, Part):
                raise SyntaxError(f'Illegal part {part!r}')
        match = re.fullmatch(r'(\d+)/(\d+)', time)
        if not match:
            raise SyntaxError(f'Illegal time signature "{time}"')
        beats, beat_type = int(match.group(1)), int(match.group(2))
        if not beats or beat_type not in (1, 2, 4, 8, 16, 32, 64):
            raise SyntaxError(f'Illegal time signature "{time}"')
        self.parts = parts
        self.time = time
        self.beats = beats
        self.beat_type = beat_type

    def __str__(self):
        return f'{", ".join(str(part) for part in self.parts)} in {self.time}'

    def __repr__(self):
        return f'Score({", ".join(repr(part) for part in self.parts)}, {self.time!r})'

    def show(self):
        from . import render_verovio
        render_verovio.show_score(self)

    def play(self):
        from . import playback
        playback.play(self)

    def _repr_svg_(self):
        self.play()
        self.show()
        return None
