# solfa

A programmable library for composing music. Draft stage: an `Idea` is content (degrees) plus
a rhythm, combined with operators, mapped through palettes, and rendered to notation via Verovio.

## Setup

Create the virtualenv and install the dependencies (Python 3.14):

```
python3 -m venv .venv
.venv/bin/pip install verovio==6.2.1 jupyterlab ipykernel
.venv/bin/python -m ipykernel install --user --name solfa --display-name "Python (solfa)"
```

The last command registers the venv as a Jupyter kernel so notebooks can import `solfa`. It writes to
`~/Library/Jupyter/kernels/solfa`; run it again after recreating the venv.

`verovio` is pinned to 6.2.1 because 6.3.0 publishes cp310 wheels only, and this venv is Python 3.14.

## Running Jupyter Notebook

From the project directory:

```
.venv/bin/jupyter notebook
```

Jupyter prints a URL (`http://localhost:8888/lab?token=...`) — open it in a browser. Notebook startup is slow
the first time while JupyterLab builds its assets.

In the notebook, pick the **Python (solfa)** kernel from the kernel menu (right-hand corner of the toolbar, or
`Kernel → Change Kernel`). Without it the notebook starts on a different interpreter and `import solfa` fails.

Stop the server with `Ctrl-C`.

## Using solfa in a notebook

```python
from solfa import deg, pit, rhy, major_scale, show

melody = deg('1 2 3 1') @ rhy('4 4 4 2') >> major_scale('c')
melody.show()                              # renders the line inline
```

An `Idea` has two slots: `content` (degrees) and `rhythm`. Either may be missing. Three levels of
operator combine ideas, tightest first:

```
@       composes:   rhythm @ degrees layers a rhythm onto notes;
                    degrees @ degrees stacks (the left pattern is the outer loop).
*       repeats:    idea * 3 repeats an idea (same level as @).
+       sequences:  a + b plays a, then b.
>> <<   maps:       degrees >> palette maps degrees through a palette;
                    notes << palette recovers their degrees.
```

```python
rhy('8') @ deg('1 2 3')             # three notes, each an eighth (looping rhythm)
deg('1 3 5') >> major_scale('c')    # c4 e4 g4
deg('1 2') + deg('5')               # 1 2 5
deg('1 2') * 3                      # 1 2 1 2 1 2
```

An idea also transposes. An interval is a degree on the same number line as notes: `1`
is the unison, `2` up a second, `0` down a second, `-1` down a third, `-2` down a fourth.
`trans(interval, up=False)` mirrors it around the
unison, so `2` becomes down a second. The interval keeps its *sound*, spelled through the
white keys: a fourth above `f4` is `bb4`, not `b4`. `diatrans(interval)` instead moves by
whole letter-steps, keeping each note's accidental: a fourth above `f4` is `b4`.

```python
pit('c4 e4 g4').trans('4#')     # f#4 a#4 c#5
pit('c4 e4 g4').trans('0')      # b3 d#4 f#4   (a second down)
pit('c4 e4 g4').trans('-1')     # a3 c#4 e4    (a third down)
pit('c4').trans('2', up=False)  # bb3          (a second down)
pit('f4').trans('4')            # bb4  (a perfect fourth)
pit('f4').diatrans('4')         # b4   (the letter, not the sound)
```

An idea also indexes and slices like a list, over the events as they play — each note or rest with
its duration. A single index is a one-event idea, a slice a shorter idea; the slice carries the
durations it actually plays, so `i[:2] + i[2:]` plays the same as `i`, and an empty selection is the
empty idea:

```python
melody = deg('1 2 3 4 5') @ rhy('4 |: 8')
melody[0]        # deg('1') @ rhy('4')
melody[0:-3]     # deg('1 2') @ rhy('4 8')
melody[-2:]      # deg('4 5') @ rhy('8 8')
```

## Degrees and palettes

There is one content type, `Degrees`: a list of groups, each group one note or a chord of
`(number, accidental)`. Numbers are relative to the 7-letter base with `c4` (middle C) as `1`, so
`b4` is `7`, `c5` is `8` and notes below `c4` go negative; the plain letters are the identity palette.
`pit(text)` parses letter names into degrees, the same way:

```python
deg('1 3 5')            # deg('1 3 5')  = c4 e4 g4
pit('c4 e4 g4')         # deg('1 3 5')  (the same thing)
format_pitches(pit('c4 e4 g4').content.groups)  # 'c4 e4 g4'  back to letter names
```

A palette is just another `Idea`, so `>>` maps degrees through it and `<<` is the
inverse. Its groups are flattened, and it **closes explicitly**: all but the last note form the
repeating unit, and the last note is a marker whose interval above the first note is the period — so
`c d e` repeats as `c d | e f | g a | b c …`. Write palettes with their closing octave (`c4 e g c5`,
`d4 f a d5`) to repeat by octave. Selection is `>>` too: a pattern of positions picks those notes out
of a palette, keeps the left side's chords, and flattens the palette's:

```python
deg('1 4 7') >> pit('d4 f a d5')   # d4 d5 d6
deg('2 3 4 5 6 7 8') >> major_scale('c')   # D Dorian
pit('c4 db4 c#4 d4') << major_scale('c')   # 1, 2b, 1#, 2  (spelling kept)
```

A single-note palette has period zero and just returns that note.

`major_scale(root)` and `minor_scale(root)` return the scale as an `Idea`, including the closing
octave so the period is one octave:

```python
major_scale('f')            # deg('4 5 6 7b 8 9 10 11')  = f4 g4 a4 bb4 c5 d5 e5 f5
```

## Rhythm and events

Durations are whole-note relative `Fraction`s (`1` is a whole, `1/4` a quarter). A rhythm loops over
the content; `|:` marks where the repeating part starts (`'4 |: 8'` is a quarter then eighths forever)
and `r` prefixes a rest (`'r4'`). `_realize`/`events()` unroll an idea into `(pitch group, duration)`
pairs, which is what rendering consumes:

```python
(deg('1 2 3') @ rhy('4 8')).events()   # [(c4, 1/4), (d4, 1/8), (e4, 1/4)]
```

## Scores and rendering

A `Score` is a list of `Part`s plus a time signature written as a string. A `Part` is one line of
music (in MusicXML terms a *staff*, so a piano is two parts):

```python
from solfa import Part, Score

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
| `pit(text)` | Parses `c`, `f#`, `bb3`, `<c e g>` into an `Idea` of degrees (letter input sugar). |
| `deg(text)` | Parses `1 3 5`, `<1 3 5>`, `1..5`, `2#` into an `Idea` of degrees. |
| `rhy(text)` | Parses `4 8 r4 \|: 16` into a rhythm-only `Idea`. |
| `idea @ other` | Compose: layer a rhythm onto notes (either way round), stack degrees (left is the outer loop); a rhythm on the right replaces one on the left. |
| `idea * other` | Repeat by an int (`idea * 3`). |
| `idea + other` | Play this idea, then `other`. |
| `idea[key]` | One event as a one-event idea, or a shorter idea over a slice of the events (`idea[0:-3]`). |
| `idea.trans(interval, up=True)` | Move every note by a musical interval (`'4#'`, `'0'`, `'-1'`), keeping its sound; `up=False` mirrors it. |
| `idea.diatrans(interval, up=True)` | Move every note by whole letter-steps, keeping its accidental. |
| `idea.inv(low, high)` | Chromatically mirror every degree around the axis — the sound mirrors exactly, accidentals adjusted; the rhythm is kept. |
| `idea.diainv(low, high)` | Diatonically mirror every degree around the axis — letters kept; the rhythm is kept. |
| `idea.retro(...)` | Play the idea backwards; `retrograde_degrees`/`retrograde_rhythm` pick which layers reverse. |
| `idea >> palette` | Map/select degrees through a palette (an `Idea`). |
| `idea << palette` | Recover the degrees of pitches in a palette. |
| `Degrees(groups)` | The one content type: groups of `(number, accidental)`. |
| `Degrees.map(other)` / `.unmap(other, strict=False)` | The two directions of `>>` / `<<`. |
| `parse_pitches(text)` / `format_pitches(groups)` | The letter language either way: names to degrees, degrees to names. |
| `major_scale(root)` / `minor_scale(root)` | The scale as an `Idea`. |
| `Event`/`Sequence` model | Replaced by `Idea`; `events()` unrolls one into `(group, duration)` pairs. |
| `Part(idea, name='Music')` | One staff of a score. |
| `Score(parts, time='4/4')` | A list of `Part`s and the time signature, written `'6/8'`. |
| `show(musicxml=None)` | Renders MusicXML through Verovio inline in Jupyter. |
| `show_score(score)` | Renders every part of a score. |

## Conventions

See `AGENTS.md` — no new classes or functions without design sign-off.
