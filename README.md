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
white keys: a fourth above `f4` is `bb4`, not `b4`. A bare degree is read as natural — the C
major spelling, as if resolved to the piano keyboard — and the result is written out in full,
with final accidentals. `diatrans(interval)` instead moves by
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
melody = deg('1 2 3 4 5') @ rhy('4 [8')
melody[0]        # deg('1') @ rhy('4')
melody[0:-3]     # deg('1 2') @ rhy('4 8')
melody[-2:]      # deg('4 5') @ rhy('8 8')
```

## Degrees and palettes

There is one content type, `Degrees`: a list of groups, each group one note or a chord of
`(number, accidental)`. Numbers are relative to the 7-letter base with `c4` (middle C) as `1`, so
`b4` is `7`, `c5` is `8` and notes below `c4` go negative; the plain letters are the identity palette.
`pit(text)` parses letter names into degrees, the same way. A pitch is absolute, so `pit` always
writes its accidentals out (`c#` is `1#`, `c` is `1n`).

An accidental is written when it is *final* and left off when it is the palette's to decide.
A bare number is scale-relative: `'4'` means the scale's fourth, whatever the scale spells it as.
`'4n'`, `'4#'` and `'4b'` are final: natural, sharp and flat — the `n` is how a natural is said
out loud, and it matters (`deg('1') != deg('1n')`: the one waits for the palette, the other is c4).

```python
deg('1 3 5')            # deg('1 3 5')  = c4 e4 g4
pit('c4 e4 g4')         # deg('1n 3n 5n')  (the same thing, written out)
format_pitches(pit('c4 e4 g4').content.groups)  # 'c4 e4 g4'  back to letter names
```

A palette is just another `Idea`, so `>>` maps degrees through it and `<<` is the
inverse. Its groups are flattened, and it **closes explicitly**: all but the last note form the
repeating unit, and the last note is a marker whose interval above the first note is the period — so
`c d e` repeats as `c d | e f | g a | b c …`. Write palettes with their closing octave (`c4 e g c5`,
`d4 f a d5`) to repeat by octave. A final accidental is final here too: it keeps the letter but
overrides what the scale spells, so `>>` and `<<` are inverses with the scale in the middle.
Selection is `>>` too: a pattern of positions picks those notes out of a palette, keeps the left
side's chords, and flattens the palette's:

```python
deg('1 4 7') >> pit('d4 f a d5')   # d4 d5 d6
deg('2 3 4 5 6 7 8') >> major_scale('c')   # D Dorian
deg('4n') >> major_scale('f')      # b-natural (b4): the accidental overrides the scale's b-flat
deg('3#') >> major_scale('eb')     # g#4 (the scale's g, sharped)
pit('c4 db4 c#4 d4') << major_scale('c')   # 1, 2b, 1#, 2  (exact notes come back bare)
```

A single-note palette has period zero and just returns that note.

`major_scale(root)` and `minor_scale(root)` return the scale as an `Idea`, including the closing
octave so the period is one octave:

```python
major_scale('f')            # deg('4n 5n 6n 7b 8n 9n 10n 11n')  = f4 g4 a4 bb4 c5 d5 e5 f5
```

## Rhythm and events

Durations are whole-note relative `Fraction`s (`1` is a whole, `4` a quarter). A bare number is `1/n`
of a whole, dots lengthen it (`4.`, `4..`), `r` prefixes a rest (`r4`), and a `+`-joined chain is one
longer event (`4+8` is a dotted quarter). A trailing `*n` repeats a token (`8*3`), and `[ ... ]` groups
nest and may be repeated; `[k: ...]` is a tuplet, the notes sitting in the time of the largest power of
two below `k` (`[3: 8 8 8]`), and `[k j: ...]` overrides that ratio (`[7 8: 16*7]`). A tuplet keeps the
ratio as a bracket around its written notes, so `rhy('[3: 8 8 8]')` is three `8`s under a `3:2` marker
and renders as a triplet bracket, not as three flattened `12`s. A rhythm loops over
the content. An unclosed `[` marks where
the repeating part starts (`'4 [8'` is a quarter then eighths forever); without one the whole rhythm
repeats, and when unclosed brackets nest it is the innermost one that loops. On its own a cycling
rhythm is infinite, so it needs content or a bounded slice.
`_realize`/`events()` unroll an idea into `(pitch group, duration)` pairs — `events()` already scaled
by the tuplets — which is what rendering consumes:

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
types, dots and tuplet ratios — a tuplet emits `<time-modification>` plus a `<tuplet>` start/stop so
the bracket is drawn, numbered by nesting depth — and `divisions` is derived from the least common
multiple of the denominators so every duration lands on a whole tick. Beaming follows the meter,
rests and lone notes break runs, and beams never cross a barline. A note that would cross a barline
is split at the bar and tied. Accidentals are written where they change the sound: a sharp or flat
when it alters a pitch, and a natural when a note cancels an accidental already written earlier in
the same bar.

## Current API

| | |
|---|---|
| `Idea(content=None, rhythm=None)` | Content (a `Degrees`) plus a rhythm. Empty is the identity for `+`. |
| `pit(text)` | Parses `c`, `f#`, `bb3`, `<c e g>` into an `Idea` of degrees (letter input sugar; pitches are absolute, so accidentals come out written). |
| `deg(text)` | Parses `1 3 5`, `<1 3 5>`, `1..5`, `2#`, `4n` into an `Idea` of degrees; a bare number is scale-relative, `n`/`#`/`b` are final. |
| `rhy(text)` | Parses `4 8 r4 [16` into a rhythm-only `Idea`. |
| `idea @ other` | Compose: layer a rhythm onto notes (either way round), stack degrees (left is the outer loop); a rhythm on the right replaces one on the left. |
| `idea * other` | Repeat by an int (`idea * 3`). |
| `idea + other` | Play this idea, then `other`. |
| `idea[key]` | One event as a one-event idea, or a shorter idea over a slice of the events (`idea[0:-3]`). |
| `idea.trans(interval, up=True)` | Move every note by a musical interval (`'4#'`, `'0'`, `'-1'`), keeping its sound; `up=False` mirrors it. |
| `idea.diatrans(interval, up=True)` | Move every note by whole letter-steps, keeping its accidental. |
| `idea.inv(low, high)` | Chromatically mirror every degree around the axis — the sound mirrors exactly, accidentals adjusted (a bare degree reads as natural); the rhythm is kept. |
| `idea.diainv(low, high)` | Diatonically mirror every degree around the axis — letters kept, a bare degree stays bare; the rhythm is kept. |
| `idea.retro(...)` | Play the idea backwards; `retrograde_degrees`/`retrograde_rhythm` pick which layers reverse. |
| `idea >> palette` | Map/select degrees through a palette (an `Idea`); a final accidental overrides the scale's, keeping the letter. |
| `idea << palette` | Recover the degrees of pitches in a palette; exact scale notes come back bare, alterations keep their accidental. |
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
