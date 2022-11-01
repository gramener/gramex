"""Module to get fontwidth."""
import os
import json
import numpy as np
from io import open

abs_path = os.path.dirname(os.path.abspath(__file__))


def fontwidth(string, font='sans-serif'):
    """Function: Returns the px width of a string assuming a base size of 16px."""
    with open(os.path.join(abs_path, 'fonts.json'), encoding='utf-8') as handle:
        _fontwidth = json.load(handle)
    codes_len = 127
    default_width = 32
    default_width_idx = 120
    for _fontrow in _fontwidth:
        _fontrow['widths'] = np.array(_fontrow['widths'], dtype=float)
        _fontrow['widths'] = np.insert(_fontrow['widths'], 0, np.zeros(default_width))

    # Add the first font stack at the end, making it the default
    _fontwidth.append(_fontwidth[0])
    # Convert all characters to ASCII codes. Treat Unicode as single char
    codes = np.fromstring(string.encode('ascii', 'replace'), dtype=np.uint8)
    # Drop everything that's out of bounds. We'll adjust for them later
    valid = codes[codes < codes_len]
    # Get the font
    for row in _fontwidth:
        if font in row['family']:
            break
    # Compute and return the width, defaulting unknowns to 'x' (char 120)
    widths = row['widths']
    return widths[valid].sum() + widths[default_width_idx] * (len(codes) - len(valid))
