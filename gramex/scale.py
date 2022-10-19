_color_convert = {'rgba': lambda v: v}


def color(domain, range, bin=False, to='hex', name='Gramex color'):
    '''
    Returns a function that scales a number in domain to a color in the range.

    - ``color(domain=[0, 1], range=['white', 'blue'])``
      maps values between 0 to 1 smoothly from white to blue.

    Use multiple colors in a smooth gradient.

    - ``color(domain=[-1, 0, 1], range=['red', 'yellow', 'green'])``
      maps values between -1 to +1 smoothly from red to yellow to green

    Use multiple colors discretely by binning into buckets (called quantization).

    - ``color(domain=[-1, 0, 1], range=['red', 'green'], bin=True)``
      maps (-1, 0) to red, and (0, 1) to green
    '''
    import numpy as np
    import matplotlib.colors as colors
    import matplotlib.cm as cm

    if bin:
        norm = colors.BoundaryNorm(boundaries=domain, ncolors=len(domain) - 1, clip=True)
    else:
        norm = colors.Normalize(min(domain), max(domain))

    if isinstance(range, str):
        cmap = getattr(cm, range, None)
        if cmap is None:
            raise ValueError(f'color(range={range}) invalid color map. See https://bit.ly/3lsdun6')
        if bin:
            n = len(domain) - 1
            cmap = colors.ListedColormap(cmap(np.linspace(0, 1, n)), name)
    elif isinstance(range, (tuple, list)):
        if bin:
            if len(range) != len(domain) - 1:
                err = 'color(domain=%r, range=%r, bin=True) invalid. len(range) != len(domain) - 1'
                raise ValueError(err % (domain, range))
            cmap = colors.ListedColormap(range, name)
        else:
            # We need either domain length = range length (one-to-one mapping)
            if len(range) == len(domain) and len(domain) > 1:
                segmentdata = [(norm(v), range[i]) for i, v in enumerate(domain)]
            # OR range length = 2, and domain has at least 2 elements (map min & max of domain)
            elif len(range) == 2 and len(domain) > 1:
                segmentdata = range
            else:
                err = 'color(domain=%r, range=%r) invalid. Need equal arrays with 2+ values'
                raise ValueError(err % (domain, range))
            cmap = colors.LinearSegmentedColormap.from_list(name, segmentdata)
    else:
        raise ValueError('color(range=%r) not a color list/map https://bit.ly/3lsdun6' % range)

    # If convertors are not present, add them.
    # Run on demand (not when module loads) to defer importing numpy.
    if to == 'hex' and 'hex' not in _color_convert:
        _color_convert['hex'] = _make_convertor(
            colors.to_hex,
        )
    elif to == 'rgb' and 'rgb' not in _color_convert:
        _color_convert['rgb'] = _make_convertor(colors.to_rgb)
    convert = _color_convert[to]
    return lambda v: convert(cmap(norm(v)))


def _make_convertor(method):
    import numpy as np

    return lambda v: method(v) if isinstance(v, tuple) else np.apply_along_axis(method, 1, v)
