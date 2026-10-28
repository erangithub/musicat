from .idea import Idea, deg
from .pitches import parse_pitches

def scale_mode(deg_str, root_str, mode):
    p, acc = parse_pitches(root_str).groups[0][0]
    return (deg('1..8').diatrans(mode) >> deg(deg_str).trans((mode, None), up=False)).trans((p, acc))



def major(root_str, mode=1):
    return scale_mode('1..8', root_str, mode)

def minor(root_str, mode=1):
    """The major scale on `root_str` as an idea, closing on its octave."""
    return major(root_str, mode=mode-2)

def melodic_minor(root_str, mode=1):
    return scale_mode('1..3b..8', root_str, mode)

def wholetone(root_str):
    """The major scale on `root_str` as an idea, closing on its octave."""
    p, acc = parse_pitches(root_str).groups[0][0]
    return deg('1 2').trans((p, acc))

