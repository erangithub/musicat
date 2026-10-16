# complib

A programmable library for composing music. Draft stage: an `Idea` is content (degrees) plus
a rhythm, combined with operators, resolved through palettes, and rendered to notation via Verovio.

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
from complib import degrees, pitches, rhythm, major_scale, show

melody = degrees('1 2 3 1') * rhythm('4 4 4 2') >> major_scale('c')
melody.show()                              # renders the line inline
```

An `Idea` has two slots: `content` (degrees) and `rhythm`. Either may be missing. Three levels of
operator combine ideas, tightest first:

```
*       builds:     rhythm * degrees layers a rhythm onto notes;
                    degrees * degrees stacks; idea * 3 repeats.
+       sequences:  a + b plays a, then b; a + pitch transposes up,
                    a - pitch transposes down.
>> <<   resolves:   degrees >> palette selects/resolves through a palette;
                    notes << palette recovers their degrees.
```

```python
rhythm('8') * degrees('1 2 3')             # three notes, each an eighth (looping rhythm)
degrees('1 3 5') >> major_scale('c')       # c4 e4 g4
degrees('1 2') + degrees('5')              # 1 2 5
degrees('1 2') * 3                         # 1 2 1 2 1 2
```

An idea also transposes, by a degree or a string like `'4#'` / `'-4#'` (the minus
goes down), through a plane. The accidental is whatever the plane's values leave
over, so with the default plane (the white keys, whose degrees are semitones) it is
exactly adding a `Pitch`; pass another `Degrees` to measure in a different plane:

```python
pitches('c4 e4 g4').transpose('4#')                          # f#4 a#4 c#5
pitches('c4 e4 g4').transpose('-4#')                         # gb3 bb3 db4
pitches('c4 e4 g4').transpose('3', Degrees(parse_degrees('0 2 3 5 7 8 10 12')))  # e4 gb4 b4
```

## Degrees and palettes

There is one content type, `Degrees`: a list of groups, each group one note or a chord of
`(number, accidental)`. Numbers are relative to the 7-letter base with `c4` (middle C) as `1`, so
`b4` is `7`, `c5` is `8` and notes below `c4` go negative; the plain letters are the identity palette.
`pitches(text)` parses letter names into the same type as input sugar:

```python
degrees('1 3 5')            # Degrees('1 3 5')  = c4 e4 g4
pitches('c4 e4 g4')         # degrees('1 3 5')  (the same thing)
pitches('c4').content.pitch()   # [[Pitch('c4')]]  materialise the I/O value
```

A palette is just another `Idea`/`Degrees`, so `>>` composes degrees through it and `<<` is the
inverse. Its groups are flattened, and it **closes explicitly**: all but the last note form the
repeating unit, and the last note is a marker whose interval above the first note is the period — so
`c d e` repeats as `c d | e f | g a | b c …`. Write palettes with their closing octave (`c4 e g c5`,
`d4 f a d5`) to repeat by octave. Selection is `>>` too: a pattern of positions picks those notes out
of a palette, keeps the left side's chords, and flattens the palette's:

```python
degrees('1 4 7') >> pitches('d4 f a d5')   # d4 d5 d6
degrees('2 3 4 5 6 7 8') >> major_scale('c')   # D Dorian
pitches('c4 db4 c#4 d4') << major_scale('c')   # 1, 2b, 1#, 2  (spelling kept)
```

A single-note palette has period zero and just returns that note.

`major_scale(root)` and `minor_scale(root)` return the scale as `Degrees`, including the closing
octave so the period is one octave:

```python
major_scale('f')            # Degrees('4 5 6 7b 8 9 10 11')  = f4 g4 a4 bb4 c5 d5 e5 f5
```

## Rhythm and events

Durations are whole-note relative `Fraction`s (`1` is a whole, `1/4` a quarter). A rhythm loops over
the content; `|:` marks where the repeating part starts (`'4 |: 8'` is a quarter then eighths forever)
and `r` prefixes a rest (`'r4'`). `_realize`/`events()` unroll an idea into `(pitch group, duration)`
pairs, which is what rendering consumes:

```python
(degrees('1 2 3') * rhythm('4 8')).events()   # [(c4, 1/4), (d4, 1/8), (e4, 1/4)]
```

## Scores and rendering

A `Score` is a list of `Part`s plus a time signature written as a string. A `Part` is one line of
music (in MusicXML terms a *staff*, so a piano is two parts):

```python
from complib import Part, Score

score = Score([Part(melody, 'Flute'), Part(accomp, 'Piano RH')], '6/8')
str(score)          # Flute, Piano RH in 6/8
score.show()        # or melody.show() for a single line
```

`show(musicxml)` renders raw MusicXML through Verovio and displays it inline (defaults to
`mock/probe.musicxml`); `show_score(score)` renders a whole score. Durations map to MusicXML note
types, dots and tuplet ratios, and `divisions` is derived from the least common multiple of the
denominators so every duration lands on a whole tick. Beaming follows the meter, rests and lone
notes break runs, and beams never cross a barline.

## Current API

| | |
|---|---|
| `Idea(content=None, rhythm=None)` | Content (a `Degrees`) plus a rhythm. Empty is the identity for `+`. |
| `pitches(text)` | Parses `c`, `f#`, `bb3`, `<c e g>` into an `Idea` of degrees (letter input sugar). |
| `degrees(text)` | Parses `1 3 5`, `<1 3 5>`, `1..5`, `2#` into an `Idea` of degrees. |
| `rhythm(text)` | Parses `4 8 r4 \|: 16` into a rhythm-only `Idea`. |
| `idea * other` | Layer a rhythm onto notes, stack degrees, or repeat by an int. |
| `idea + other` | Play this idea, then `other`. |
| `idea.transpose(interval, palette=None)` | Move every note by a degree (or `'4#'`/`'-4#'`) through a plane (the white keys by default). |
| `idea >> palette` | Compose/select/resolve degrees through a palette (an `Idea` or `Degrees`). |
| `idea << palette` | Recover the degrees of pitches in a palette. |
| `Degrees(groups)` | The one content type: groups of `(number, accidental)`. |
| `Degrees.compose(other)` / `.decompose(other, strict=False)` | The two directions of `>>` / `<<`. |
| `Degrees.pitch()` | Materialise as groups of `Pitch` (the I/O value). |
| `major_scale(root)` / `minor_scale(root)` | The scale as `Degrees`. |
| `Pitch(name)` | Parses `c`, `f#`, `bb3`, `c-1`; `midipitch()` is the MIDI number. |
| `Event`/`Sequence` model | Replaced by `Idea`; `events()` unrolls one into `(group, duration)` pairs. |
| `Part(idea, name='Music')` | One staff of a score. |
| `Score(parts, time='4/4')` | A list of `Part`s and the time signature, written `'6/8'`. |
| `show(musicxml=None)` | Renders MusicXML through Verovio inline in Jupyter. |
| `show_score(score)` | Renders every part of a score. |

## Conventions

See `AGENTS.md` — no new classes or functions without design sign-off.
