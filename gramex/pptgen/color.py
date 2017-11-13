"""
A color and gradient management system.

*Do not pick colors yourself*. A lot of research has gone into color
palettes. Specifically, for:

Numeric data
    use `ColorBrewer <http://colorbrewer2.org/>`_ themes

Non-numeric data
    use `ColorBrewer <http://colorbrewer2.org/>`_
    or `Microsoft Office themes`_

Page design
    use `kuler.adobe.com <https://kuler.adobe.com/#create/fromanimage>`_
    *from an image* (not directly).


Microsoft office themes
-----------------------

The following color palettes based on Microsoft Office are available:

Office, Adjacency, Apex, Apothecary, Aspect, Austin, BlackTie, Civic, Clarity,
Composite, Concourse, Couture, Elemental, Equity, Essential, Executive, Flow,
Foundry, Grid, Hardcover, Horizon, Median, Metro, Module, Newsprint, Opulent,
Oriel, Origin, Paper, Perspective, Pushpin, SlipStream, Solstice, Technic,
Thatch, Trek, Urban, Verve, Waveform

A palette's colours can be accessed as an array or as an attribute. For e.g.:

>>> Office[0]               # The first element
u'#4f81bd'
>>> Office.accent_1         # ... is called .accent_1
u'#4f81bd'
>>> Office[1]               # The next element
u'#c0504d'
>>> Office.accent_2         # ... is called .accent_2
u'#c0504d'

The following 10 attributes are available (in order):

0. accent_1
1. accent_2
2. accent_3
3. accent_4
4. accent_5
5. accent_6
6. light_2
7. dark_2
8. light_1
9. dark_1

"""

import os
import re
import six
import json
import operator
import colorsys
import warnings
import numpy as np
from io import open


BASE_0 = 0
BASE_1 = 1
BASE_2 = 2
BASE_3 = 3
BASE_4 = 4
BASE_5 = 5
BASE_7 = 7
BASE_9 = 9
BASE_15 = 15
BASE_16 = 16
BASE_255 = 255
BASE_256 = 256


class _MSO(object):
    """
    Microsoft office themes. Refer to colors in any of these ways:

        color['accent_1']
        color[0]
        color.accent_1
        color[:1]
    """

    _lookup = {
        'accent_1': 0,
        'accent_2': 1,
        'accent_3': 2,
        'accent_4': 3,
        'accent_5': 4,
        'accent_6': 5,
        'light_2': 6,
        'dark_2': 7,
        'light_1': 8,
        'dark_1': 9,
    }

    def __init__(self, *values):
        self.values = values

    def __getitem__(self, key):
        if isinstance(key, slice) or type(key) is int:
            return self.values.__getitem__(key)
        elif key in self._lookup:
            return self.values[self._lookup[key]]

    def __getattr__(self, key):
        if key in self._lookup:
            return self.values[self._lookup[key]]

    def __len__(self):
        return len(self.values)

    def __str__(self):
        return ' '.join(self.values)

    def __repr__(self):
        return '_MSO' + repr(self.values)


def _rgb(color):
    """
    .. deprecated:: 0.1
        Use :func:`rgba` instead
    """
    warnings.warn('Use color.rgba instead of color._rgb',
                  FutureWarning, stacklevel=2)
    return (int(color[-6:-4], BASE_16), int(color[-4:-2], BASE_16),
            int(color[-2:], BASE_16))


def gradient(value, grad, opacity=1, sort=True):
    """
    Converts a number or list ``x`` into a color using a gradient.


    :arg number value: int, float, list, numpy array or any iterable.
        If an iterable is passed, a list of colors is returned.
    :arg list grad: tuple/list of ``(value, color)`` tuples
        For example, ``((0, 'red'), (.5, 'yellow'), (1, 'green'))``.
        Values will be sorted automatically
    :arg float opacity: optional alpha to be added to the returned color
    :arg bool sort: optional. If ``grad`` is already sorted, set ``sort=False``

    These gradients are available:

    **divergent gradients** : on a ``[-1, 1]`` scale
        multi-color
            ``RdGy``, ``RdYlGn``, ``Spectral``
        ... also print-friendly and color-blind safe
            ``BrBG``, ``PiYG``, ``PRGn``, ``RdBu``, ``RdYlBu``
        ... and also photocopyable
            ``PuOr``
    **sequential gradients** : on a ``[0, 1]`` scale
        one-color
            ``Reds``, ``Blues``, ``Greys``, ``Greens``, ``Oranges``,
            ``Purples``, ``Browns``, ``Yellows``
        two-color
            ``BuGn``, ``BuPu``, ``GnBu``, ``OrRd``, ``PuBu``, ``PuRd``,
            ``RdPu``, ``YlGn``
        three-color
            ``YlGnBu``, ``YlOrBr``, ``YlOrRd``, ``PuBuGn``

    The following are also available, but do not use them.

    - ``RYG`` maps ``[0, 1]`` to Red-Yellow-Green
    - ``RWG`` maps ``[0, 1]`` to Red-White-Green
    - ``RYG_1`` maps ``[-1, -1]`` to Red-Yellow-Green
    - ``RWG_1`` maps ``[-1, -1]`` to Red-White-Green

    Examples::

        # Get a value that is 40% blue and 60% white, use:
        >>> gradient(0.4, ((0, 'blue'), (1, 'white')))
        '#66f'

        # A list (or any iterable) input returns a list of colors
        >>> gradient([0.2, 0.6, 0.8], ((0, 'blue'), (1, 'white')))
        ['#33f', '#99f', '#ccf']

        # Values out of range are truncated.
        >>> gradient([-10, +10], ((0, 'blue'), (1, 'white')))
        ['blue', 'white']

        # Use a pre-defined gradient to classify a value between -1 to 1 on a
        # Red-Yellow-Green scale. (Returns a value between Yellow and Green).
        >>> gradient(0.5, RdYlGn)
        '#8ccb87'
    """
    if sort:
        grad = sorted(grad, key=operator.itemgetter(BASE_0))

    # If value is iterable, apply gradient to each value (recursively)
    if np.ndim(value) > BASE_0:
        return [gradient(val, grad, opacity=opacity, sort=False)
                for val in value]

    value = float(value) if not np.isnan(value) else BASE_0
    if value <= grad[BASE_0][BASE_0]:
        return grad[BASE_0][BASE_1]

    grd_idx = -1
    if value >= grad[grd_idx][BASE_0]:
        return grad[grd_idx][BASE_1]
    i = BASE_0
    for i, (start, color1) in enumerate(grad):
        if value <= start:
            break
    dist1 = (value - grad[i - BASE_1][BASE_0]) / (
        grad[i][BASE_0] - grad[i - BASE_1][BASE_0])

    sec_dist = 1.0
    dist2 = sec_dist - dist1
    color1 = rgba(grad[i - BASE_1][BASE_1])
    color2 = rgba(grad[i][BASE_1])
    return name(color1[BASE_0] * dist2 + color2[BASE_0] * dist1,
                color1[BASE_1] * dist2 + color2[BASE_1] * dist1,
                color1[BASE_2] * dist2 + color2[BASE_2] * dist1,
                opacity)


_DISTINCTS = [
    "#1f77b4", "#aec7e8",
    "#ff7f0e", "#ffbb78",
    "#2ca02c", "#98df8a",
    "#d62728", "#ff9896",
    "#9467bd", "#c5b0d5",
    "#8c564b", "#c49c94",
    "#e377c2", "#f7b6d2",
    "#7f7f7f", "#c7c7c7",
    "#bcbd22", "#dbdb8d",
    "#17becf", "#9edae5"
]


def distinct(count):
    """
    Generates a list of ``count`` distinct colors, for up to 20 colors.

    :arg int count: number of colors to return

    Examples::

        >>> distinct(4)
        ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    Notes:

    - Colour conversion between RGB and HCL are available on
      `color.py <http://2sn.org/python/color.py>`_ and
      `python-colormath <http://python-colormath.readthedocs.org/>`_
    - People seem to struggle with about
      `26 colours
      <http://eleanormaclure.files.wordpress.com/2011/03/colour-coding.pdf>`_
      so this may be an upper bound
    - A good starting point for resources is on
      `stackoverflow <http://stackoverflow.com/q/470690/100904>`_ and the
      `graphic design <http://graphicdesign.stackexchange.com/q/3682>`_
      stackexchange
    - More palettes are available from
      `Kenneth Kelly (22) <http://www.iscc.org/pdf/PC54_1724_001.pdf>`_ and
      `ggplot2 <http://learnr.wordpress.com/2009/04/15/ggplot2/>`_
    - See also: http://epub.wu.ac.at/1692/1/document.pdf
    """
    tens_count = 10
    twenty_count = 20
    _distinct = 2
    if count <= tens_count:
        return [_DISTINCTS[_distinct * i] for i in range(count)]
    elif count <= twenty_count:
        return _DISTINCTS[:count]
    else:
        return _DISTINCTS[:]


def contrast(color, white='#ffffff', black='#000000'):
    """
    Returns the colour (white or black) that contrasts best with a given
    color.

    :arg color color: color string recognied by :func:`rgba`.
        If this color is dark, returns white. Else, black
    :arg color white: color string, optional.
        Replace this with any light colour you want to use instead of white
    :arg color black: color string, optional.
        Replace this with any dark colour you want to use instead of black

    Examples::

        >>> contrast('blue')
        '#fff'
        >>> contrast('lime')
        '#000'

    Note: `Decolorize <http://www.eyemaginary.com/Rendering/TurnColorsGray.pdf>`_
    algorithm used. Appears to be the most preferred
    (`ref <http://dcgi.felk.cvut.cz/home/cadikm/color_to_gray_evaluation/>`_).
    """
    idx = 3
    red, green, blue = rgba(color)[:idx]
    red_opac = 0.299
    blue_opac = 0.114
    green_opac = 0.582
    cut_off = .5

    luminosity = red_opac * red + green_opac * green + blue_opac * blue
    return black if luminosity > cut_off else white


def brighten(color, percent):
    """
    Brighten or darken a color by percentage. If ``percent`` is positive,
    brighten the color. Else darken the color.

    :arg str color: color string recognied by :func:`rgba`
    :arg float percent: -1 indicates black, +1 indicates white. Rest are interpolated.

    Examples::

        >>> brighten('lime', -1)    # 100% darker, i.e. black
        '#000'
        >>> brighten('lime', -0.5)  # 50% darker
        '#007f00'
        >>> brighten('lime', 0)     # Returns the color as-is
        '#0f0'
        >>> brighten('lime', 0.5)   # 50% brighter
        '#7fff7f'
        >>> brighten('lime', 1)     # 100% brighter, i.e. white
        '#fff'
        >>> brighten('lime', 2)     # Values beyond +1 or -1 are truncated
        '#fff'
    """
    _min = -1
    _mid = 0
    _max = +1
    black = '#0000000'
    white = '#ffffff'
    return gradient(percent, ((_min, black), (_mid, color), (_max, white)))


def msrgb(value, grad=None):
    """
    Returns the Microsoft
    `RGB color <http://msdn.microsoft.com/en-in/library/dd355244.aspx>`_
    corresponding to a given a color. This is used for Microsoft office
    output (e.g. Excel, PowerPoint, etc.)

    :arg color value: color or int/float. If ``grad`` is not specified, this
        should be a color that will get converted into a Microsoft RGB value. If
        ``grad`` is specified, this should be a number. It will be converted into
        a color using the gradient, and then into a Microsoft RGB value.
    :arg tuple grad: tuple/list of ``(value, color)`` tuples For example, ``((0,
        'red'), (.5, 'yellow'), (1, 'green'))``. This is passed as an input to
        :func:`gradient`

    Examples::

        >>> msrgb('#fff')
        16777215
        >>> msrgb('red')
        255
        >>> msrgb(0.5, RYG) # == msrgb(gradient(0.5, RYG))
        65535
    """
    idx = 3
    red, green, blue = rgba(gradient(value, grad) if grad else value)[:idx]
    return int((blue * BASE_255 * BASE_256 + green * BASE_255) * BASE_256 + red * BASE_255)


def msrgbt(value, grad=None):
    """
    Returns the Microsoft RGB value (same as :func:`msrgbt`) and transparency
    as a tuple.

    For example::

        color, transparency = msrgbt('rgba(255, 0, 0, .5)')
        shp.Fill.ForeColor.RGB, shp.Fill.Transparency = color, transparency

    See :func:`msrgbt`. The parameters are identical.

    Examples::

        >>> msrgbt('rgba(255,0,0,.5)')
        (255, 0.5)
        >>> msrgbt('red')
        (255, 0.0)
    """
    _alpha = 1
    red, green, blue, alpha = rgba(gradient(value, grad) if grad else value)
    alpha = _alpha - alpha
    col = (blue * BASE_255 * BASE_256 + green * BASE_255) * BASE_256 + red * BASE_255
    return int(col), alpha


def rgba(color):
    """
    Returns red, green, blue and alpha values (as a 0-1 float) of a color.

    :arg color color: a string representing the color.
        Most color formats defined in
        `CSS3 <http://dev.w3.org/csswg/css3-color/>`_ are allowed.

    Examples::

        >>> rgba('#f00')
        (1.0, 0.0, 0.0, 1.0)
        >>> rgba('#f003')
        (1.0, 0.0, 0.0, 0.2)
        >>> rgba('#ff0000')
        (1.0, 0.0, 0.0, 1.0)
        >>> rgba('#ff000033')
        (1.0, 0.0, 0.0, 0.2)
        >>> rgba('rgb(255,0,0)')
        (1.0, 0.0, 0.0, 1.0)
        >>> rgba('rgba(255,0,0,.2)')
        (1.0, 0.0, 0.0, 0.2)
        >>> rgba('red')
        (1.0, 0.0, 0.0, 1.0)
        >>> rgba('white')
        (1.0, 1.0, 1.0, 1.0)
        >>> rgba('hsl(0,1,1)')
        (1.0, 0.0, 0.0, 1.0)
        >>> rgba('hsla(0,1,1,.2)')
        (1.0, 0.0, 0.0, 0.2)
        >>> rgba('hsl(0, 100%, 50%)')
        (0.5, 0.0, 0.0, 1.0)
        >>> rgba('hsla(0, 100%, 100%, .9)')
        (1.0, 0.0, 0.0, 0.9)
        >>> rgba('hsla(360, 100%, 100%, 1.9)')
        (1.0, 0.0, 0.0, 1.0)
        >>> rgba('hsla(360, 0%, 50%, .5)')
        (0.5, 0.5, 0.5, 0.5)
        >>> rgba('hsla(0, 0%, 50%, .5)')
        (0.5, 0.5, 0.5, 0.5)
    """
    result = []
    if color.startswith('#'):
        if len(color) == BASE_9:
            result = [int(color[BASE_1:BASE_3], BASE_16) / float(BASE_255),
                      int(color[BASE_3:BASE_5], BASE_16) / float(BASE_255),
                      int(color[BASE_5:BASE_7], BASE_16) / float(BASE_255),
                      int(color[BASE_7:BASE_9], BASE_16) / float(BASE_255)]
        elif len(color) == BASE_7:
            result = [int(color[BASE_1:BASE_3], BASE_16) / float(BASE_255),
                      int(color[BASE_3:BASE_5], BASE_16) / float(BASE_255),
                      int(color[BASE_5:BASE_7], BASE_16) / float(BASE_255)]
        elif len(color) == BASE_5:
            result = [int(color[BASE_1:BASE_2], BASE_16) / float(BASE_15),
                      int(color[BASE_2:BASE_3], BASE_16) / float(BASE_15),
                      int(color[BASE_3:BASE_4], BASE_16) / float(BASE_15),
                      int(color[BASE_4:BASE_5], BASE_16) / float(BASE_15)]
        elif len(color) == BASE_4:
            result = [int(color[BASE_1:BASE_2], BASE_16) / float(BASE_15),
                      int(color[BASE_2:BASE_3], BASE_16) / float(BASE_15),
                      int(color[BASE_3:BASE_4], BASE_16) / float(BASE_15)]
        else:
            result = []

    elif color.startswith('rgb(') or color.startswith('rgba('):
        for i, val in enumerate(re.findall(r'[0-9\.%]+', color.split('(')[1])):
            if val.endswith('%'):
                result.append(float(val[:-1]) / 100)
            elif i < 3:
                result.append(float(val) / float(BASE_255))
            else:
                result.append(float(val))

    elif color.startswith('hsl(') or color.startswith('hsla('):
        for i, val in enumerate(re.findall(r'[0-9\.%]+', color.split('(')[BASE_1])):
            if val.endswith('%'):
                val_idx = -1
                div = 100
                result.append(float(val[:val_idx]) / div)
            elif i == BASE_0:
                div_base = 360
                result.append(float(val) / div_base % BASE_1)
            else:
                result.append(float(val))
        result[BASE_0], result[BASE_1], result[BASE_2] = colorsys.hsv_to_rgb(
            result[BASE_0], result[BASE_1], result[BASE_2])

    elif color in _COLORNAMES:
        result = [val / float(BASE_255) for val in _COLORNAMES[color]]

    if len(result) == BASE_3:
        result.append(float(BASE_1))

    if len(result) != BASE_4:
        raise ValueError('%s: invalid color' % color)

    return tuple(
        float(BASE_0) if val < BASE_0 else float(
            BASE_1) if val > BASE_1 else val for val in result)


def hsla(color):
    """
    Returns hue, saturation, luminosity and alpha values (as a 0-1 float) for
    a color.

    :arg color color: a string representing the color.
        Most color formats defined in
        `CSS3 <http://dev.w3.org/csswg/css3-color/>`_ are allowed.

    Examples::

        >>> hsla('#f00')
        (0.0, 1.0, 1.0, 1.0)
        >>> hsla('#f003')
        (0.0, 1.0, 1.0, 0.2)
        >>> hsla('#ff0000')
        (0.0, 1.0, 1.0, 1.0)
        >>> hsla('#ff000033')
        (0.0, 1.0, 1.0, 0.2)
        >>> hsla('rgb(255,0,0)')
        (0.0, 1.0, 1.0, 1.0)
        >>> hsla('rgba(255,0,0,.2)')
        (0.0, 1.0, 1.0, 0.2)
        >>> hsla('red')
        (0.0, 1.0, 1.0, 1.0)
        >>> hsla('hsl(0,1,1)')
        (0.0, 1.0, 1.0, 1.0)
        >>> hsla('hsla(0,1,1,.2)')
        (0.0, 1.0, 1.0, 0.2)
    """
    result = rgba(color)
    return colorsys.rgb_to_hsv(
        result[BASE_0], result[BASE_1], result[BASE_2]) + (result[BASE_3], )


def name(red, green, blue, alpha=1):
    """
    Returns a short color string

    :arg float red: red color value (0-1)
    :arg float green: green color value (0-1)
    :arg float blue: blue color value (0-1)
    :arg float alpha: float, optional transparency value between 0-1.
        ``alpha=1`` produces color strings like ``#abc``
        Lower values produce ``rgba(...)```.

    Examples::

        >>> name(1, 0, 0)       # Short color versions preferred
        '#f00'
        >>> name(1, 0, 0, .2)   # Alpha creates rgba() with 2 decimals
        'rgba(255,0,0,0.20)'
        >>> name(.5, .25, .75)  # Multiply by 255 and round to nearest
        '#8040bf'
        >>> name(-1, 2, 0)      # Values are truncated to 0-1
        '#0f0'
    """
    red = int(round(
        BASE_255 * (BASE_0 if red < BASE_0 else BASE_1 if red > BASE_1 else red),
        BASE_0))

    green = int(round(
        BASE_255 * (BASE_0 if green < BASE_0 else BASE_1 if green > BASE_1 else green),
        BASE_0))

    blue = int(round(
        BASE_255 * (BASE_0 if blue < BASE_0 else BASE_1 if blue > BASE_1 else blue),
        BASE_0))

    alpha = BASE_0 if alpha < BASE_0 else BASE_1 if alpha > BASE_1 else alpha
    if alpha == BASE_1:
        return '#%02x%02x%02x' % (red, green, blue)
    else:
        return 'rgba(%d,%d,%d,%0.2f)' % (red, green, blue, alpha)


def _add_gradients(target, data):
    """Add gradients to the module"""
    mid_val = 0.5
    min_val = -1.0
    for grad, colors in six.iteritems(data['sequential']):
        target[grad] = [[float(BASE_0), colors[BASE_0]],
                        [mid_val, colors[BASE_1]],
                        [float(BASE_1), colors[BASE_2]]]
    for grad, colors in six.iteritems(data['divergent']):
        target[grad] = [[min_val, colors[BASE_0]],
                        [float(BASE_0), colors[BASE_1]],
                        [float(BASE_1), colors[BASE_2]]]
    for grad, colors in six.iteritems(data['office']):
        target[grad] = _MSO(*colors)


_DATA = json.load(open(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'colors.json'), encoding='utf-8'))
_COLORNAMES = _DATA['names']
_add_gradients(globals(), _DATA)
