# complib

A programmable library for composing music. Draft stage: pitches, scales, and notation rendering via Verovio.

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
from complib import Pitch, to_pitches, major_scale, show

[p.name for p in to_pitches('c e g')]     # ['c', 'e', 'g']
[str(p) for p in major_scale('d')]         # ['d', 'e', 'f#', 'g', 'a', 'b', 'c#']
Pitch('f#4').midipitch()                   # 66
```

`show(musicxml)` renders MusicXML with Verovio and displays the score inline in the notebook. `mock/probe.musicxml` is
a four-bar melody to try it with:

```python
show(open('mock/probe.musicxml').read())
```

Rendering is fast enough to be interactive: Verovio loads and renders that melody in under 10 ms. For
print-quality output, LilyPond (`brew install lilypond`) compiles the same music in ~0.7 s.

## Current API

| | |
|---|---|
| `Pitch(name)` | Parses `c`, `f#`, `bb3`, `c-1`. Attributes: `name`, `root`, `accidental`, `octave`. |
| `Pitch.midipitch()` | MIDI note number, e.g. `c4` → 60. Without an octave it returns the pitch class. |
| `Duration()` | A quarter note. Opaque for now — it takes no arguments. |
| `Event(pitches, duration)` | Base class: anything that occupies time. Holds a `pitches` list and a `duration`. |
| `Note(pitch, duration)` | An `Event` with one pitch. |
| `Chord(pitches, duration)` | An `Event` with two or more pitches. |
| `Rest(duration)` | An `Event` with no pitches. |
| `Event.midipitches()` | MIDI numbers of the event's pitches, e.g. `[0, 4, 7]` for `c e g`. |
| `major_scale(root)` | The seven pitches of the major scale, spelled correctly for the root (`major_scale('bb')` → `bb c d eb f g a`). |
| `to_pitches(text)` | Parses whitespace-separated pitch names into an iterator of `Pitch`. |
| `show(musicxml)` | Renders MusicXML through Verovio and displays it inline in Jupyter. |

## Conventions

See `AGENTS.md` — no new classes or functions without design sign-off.
