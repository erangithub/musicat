# complib

A programmable library for composing music. Draft stage: pitches, scales, durations, events, and notation rendering via
Verovio.

## Setup

Create the virtualenv and install the dependencies (Python 3.14):

```
python3 -m venv .venv
.venv/bin/pip install verovio==6.2.1 jupyterlab ipykernel
.venv/bin/python -m ipykernel install --user --name complib --display-name "Python (complib)"
```

The last command registers the venv as a Jupyter kernel so notebooks can import `complib`. It writes to
`~/Library/Jupyter/kernels/complib`; run it again after recreating the venv.

`verovio` is pinned to 6.2.1 because 6.3.0 publishes cp310 wheels only, and this venv is Python 3.14.

## Running Jupyter Lab

From the project directory:

```
.venv/bin/jupyter lab
```

Jupyter prints a URL (`http://localhost:8888/lab?token=...`) — open it in a browser. Notebook startup is slow
the first time while JupyterLab builds its assets.

In the notebook, pick the **Python (complib)** kernel from the kernel menu (right-hand corner of the toolbar, or
`Kernel → Change Kernel`). Without it the notebook starts on a different interpreter and `import complib` fails.

Stop the server with `Ctrl-C`.

## Using complib in a notebook

```python
from complib import Pitch, to_pitches, to_rhythm, combine, show_seq, major_scale, show

[p.name for p in to_pitches('c e g')]     # ['c', 'e', 'g']
[str(p) for p in major_scale('d')]         # ['d', 'e', 'f#', 'g', 'a', 'b', 'c#']
Pitch('f#4').midipitch()                   # 66
to_rhythm('/4 1/8. /16')                   # [1/4, 3/16, 1/16]

seq = combine(to_pitches('c e g'), to_rhythm('/4 /8'))
[str(e) for e in seq]                      # ['c 1/4', 'e 1/8', 'g 1/4']
show_seq(seq)                              # c, e, g as a quarter, an eighth, a quarter
```

`show(musicxml)` renders MusicXML with Verovio and displays the score inline in the notebook. `mock/probe.musicxml` is
a four-bar melody to try it with:

```python
show()                                     # loads mock/probe.musicxml
show(open('mock/probe.musicxml').read())
```

Rendering is fast enough to be interactive: Verovio loads and renders that melody in under 10 ms. For
print-quality output, LilyPond (`brew install lilypond`) compiles the same music in ~0.7 s.

## Durations, rhythms and events

Durations are whole-note relative `Fraction`s: `1` is a whole note, `1/4` a quarter. `to_rhythm` reads `a/b`, `/b`
(meaning `1/b`), `a`, and trailing dots for dotted values:

```python
to_rhythm('1/4 1/8. /16')      # 1/4, 3/16, 1/16
```

`combine(pitches, rhythm)` pairs pitches with durations, cycling the rhythm when it is shorter than the pitch list.
Each item is a pitch, a list of pitches (a chord), or an empty list (a rest):

```python
combine([['c', 'e'], [], to_pitches('g')], to_rhythm('1/2 1/4'))   # chord c e 1/2, rest 1/4, note g 1/2 (rhythm cycles)
```

`show_seq()` maps every duration to a MusicXML note type, dots and tuplet ratio, and derives `divisions` from the least
common multiple of the denominators so each duration lands on a whole tick. `1/5` becomes a quarter with a 5:4 time
modification, `1/12` an eighth with 3:2.

Rendering limits for now: the time signature is a hardcoded 4/4, an event that does not fit the remaining bar starts the
next bar instead of being tied across it, and tuplets carry a time modification but no bracket.

Pitches and events compare by value and are hashable:

```python
combine(to_pitches('c e g'), to_rhythm('/4 /8')) == combine(to_pitches('c e g'), to_rhythm('/4 /8'))   # True
Note('c') == Chord(['c'])      # False — a note is not a chord
Pitch('c#4') == Pitch('db4')   # False — both are MIDI 61, but the spelling differs
```

## Current API

| | |
|---|---|
| `Pitch(name)` | Parses `c`, `f#`, `bb3`, `c-1`. Attributes: `name`, `root`, `accidental`, `octave`. |
| `Pitch.midipitch()` | MIDI note number, e.g. `c4` → 60. Without an octave it returns the pitch class. |
| `Duration` | Alias for `fractions.Fraction`. Durations are whole-note relative, so `1` is a whole note. |
| `Rhythm` | Alias for `list[Duration]`. |
| `WHOLE`, `HALF`, `QUARTER`, `EIGHTH`, `SIXTEENTH`, `THIRTY_SECOND` | Note values as durations, e.g. `QUARTER` is `Fraction(1, 4)`. |
| `DOT`, `DOUBLE_DOT` | `Fraction(3, 2)` and `Fraction(7, 4)`; multiply a note value to dot it, as in `QUARTER * DOT`. |
| `Event(pitches, duration)` | Base class: anything that occupies time. Holds a `pitches` list and a `duration`. |
| `Note(pitch, duration)` | An `Event` with one pitch. |
| `Chord(pitches, duration)` | An `Event` with two or more pitches. |
| `Rest(duration)` | An `Event` with no pitches. |
| `Event.midipitches()` | MIDI numbers of the event's pitches, e.g. `[0, 4, 7]` for `c e g`. |
| `major_scale(root)` | The seven pitches of the major scale, spelled correctly for the root (`major_scale('bb')` → `bb c d eb f g a`). |
| `to_pitches(text)` | Parses whitespace-separated pitch names into a list of `Pitch`. |
| `to_rhythm(text)` | Parses whitespace-separated durations into a list of `Fraction`. |
| `combine(pitches, rhythm)` | Zips pitches with durations into a list of events, cycling the rhythm as needed. |
| `show(musicxml=None)` | Renders MusicXML through Verovio and displays it inline in Jupyter. Defaults to `mock/probe.musicxml`. |
| `show_seq(sequence)` | Renders a sequence of events as MusicXML in memory and displays it. |

## Conventions

See `AGENTS.md` — no new classes or functions without design sign-off.
