"""Mozart, Piano Sonata No. 16 in C major, K. 545 ("Sonata facile"), I. Allegro.

Bars 1-8.
"""
from solfa import Idea, Part, Score, degrees, major_scale, pitches, rhythm

C = major_scale('c')

# ---------------------------------------------------------------- right hand

# bars 1-4: two two-bar phrases
theme = degrees('8') * (degrees ('1 3 5 0 1 2 1') * rhythm('2 4 4  4. 16 16 4 r4')
         + degrees ('6 5 8 5 4 3 4 3') * rhythm('2 4 4  4 8 16 16 4 r4'))

# bars 5-8: one scale figure, a step lower each bar
run = degrees('6..13..6') * rhythm('8 |: 16')
runs = run * degrees('1 0 -1 -2')

right_hand = theme + runs >> C

# ----------------------------------------------------------------- left hand

# bars 1-4: an Alberti bass. The figure is low-high-middle-high, so it is the
# same degrees over each chord; the chord is the palette.
alberti = degrees('1 3 2 3') * rhythm('8')
tonic = '1 3 5'
chords = [tonic, tonic, '2 4 5', tonic, '1 4 6', tonic, '0 2 5', tonic]
alberti_bars = sum((alberti >> degrees(chord) >> C for chord in chords), Idea())

# bars 5-8: bass note and a dyad on the fourth beat
steps = (pitches('f4 <f3 c4>   <e3 c4> <e3 c4>   <d3 c4> <d3 b3>   <c3 c4> <c3 e3>')
         * rhythm('4 r4 r4 4'))

left_hand = alberti_bars + steps


def score():
    return Score([Part(right_hand, 'Right hand'), Part(left_hand, 'Left hand')], '4/4')


if __name__ == '__main__':
    score().show()
