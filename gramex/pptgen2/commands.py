'''
pptgen2.pptgen() modifies slides using commands (in ``__init__.py``). This file maps the commands
and their functions in ``cmdlist``.

Each command accepts ``(shape, spec, data)`` and modifies shape based on spec(ification) and data.
'''

import copy
import gramex.cache
import io
import matplotlib.cm
import matplotlib.colors
import os
import pptx
import pptx.util
import re
import requests
from PIL import Image
from functools import partial
from gramex.config import objectpath
from gramex.transforms import build_transform
from lxml.html import fragments_fromstring, builder, HtmlElement
from pptx.dml.color import RGBColor
from pptx.dml.fill import FillFormat
from pptx.enum.base import EnumValue
from pptx.enum.dml import MSO_THEME_COLOR, MSO_FILL
from pptx.enum.text import PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import _nsmap, qn
from pptx.oxml.simpletypes import ST_Percentage
from pptx.oxml.xmlchemy import OxmlElement
from pptx.text.text import _Run
from six.moves.urllib_parse import urlparse
from typing import Union, List

conf = gramex.cache.open('config.yaml', rel=True)
_nsmap.update(conf['nsmap'])


# Expression utilities
# ---------------------------------------------------------------------
def expr(val, data: dict = {}):
    if data.get('_expr_mode'):
        if isinstance(val, dict) and 'value' in val:
            val = val['value']
            val = val.format(**data) if isinstance(val, str) else val
        elif isinstance(val, str):
            vars = {key: None for key in data}
            val = build_transform({'function': str(val)}, vars=vars, iter=False)(**data)
    else:
        if isinstance(val, dict) and 'expr' in val:
            vars = {key: None for key in data}
            val = build_transform({'function': str(val['expr'])}, vars=vars, iter=False)(**data)
        elif isinstance(val, str):
            val = val.format(**data)
    return val


def assign(convert, *path: List[str]):
    '''assign(int, 'font', 'size') returns a method(para, '10') -> para.font.size = int(10)'''
    def method(node, value, data):
        for p in path[:-1]:
            node = getattr(node, p)
        # To clear the bold, italic, etc, we need to set it to None. So don't convert None
        setattr(node, path[-1], None if value is None else convert(value))
    return method


# Length utilities
# ---------------------------------------------------------------------
length_unit = pptx.util.Inches          # The default length unit is inches. This is exposed
_length_expr = re.compile(r'''          # A length expression can be:
    ([\d\.]+)                           #   Any integer or floating point (without + or -)
    \s*                                 #   optionally followed by spaces
    ("|in|inch|inches|cm|mm|pt|cp|centipoint|centipoints|emu|)  # and a unit that may be blank
    $                                   # with nothing after that
''', re.VERBOSE)
# Standardize the aliases into pptx.util attributes
length_alias = {'"': 'inches', 'in': 'inches', 'inch': 'inches',
                'centipoint': 'centipoints', 'cp': 'centipoints'}


def length_class(unit_str: str):
    '''Converts unit string like in, inch, cm, etc to pptx.util.Inches, pptx.util.Cm, etc.'''
    unit = length_alias.get(unit_str, unit_str).title()
    if hasattr(pptx.util, unit):
        return getattr(pptx.util, unit)
    elif not unit:
        return length_unit
    else:
        raise ValueError('Invalid unit: %s' % unit_str)


def length(val: Union[str, int, float]) -> pptx.util.Length:
    '''Converts 3.2, 3.2" or 3.2 inch to pptx.util.Inches(3.2) -- with specified or default unit'''
    if isinstance(val, str):
        match = _length_expr.match(val)
        if match:
            return length_class(match.group(2))(float(match.group(1)))
    elif isinstance(val, (int, float)):
        return length_unit(val)
    raise ValueError('Invalid length: %r' % val)


# Color utilities
# ---------------------------------------------------------------------
color_map = matplotlib.colors.get_named_colors_mapping()
# Theme colors can start with any of these
theme_color = re.compile(r'''
    (ACCENT|BACKGROUND|DARK|LIGHT|TEXT|HYPERLINK|FOLLOWED_HYPERLINK)
    _?(\d*)             # followed by _1, _2, etc (or 1, 2, etc.)
    (\+\d+|\-\d+)?      # There MAY be a +30 or -40 after that to adjust brightness%
''', re.VERBOSE)


def fill_color(fill: FillFormat, val: Union[str, tuple, list, None]) -> None:
    '''
    Set the FillFormat color to value specified as a:

    - a named color, like ``black``
    - a hex value, like ``#f80`` or ``#ff8800``
    - an RGB value, like ``rgb(255, 255, 0)``
    - a tuple or list of RGB values, like ``(255, 255, 0)`` or ``[255, 255, 0]``
    - a theme color, like ``ACCENT_1``, ``ACCENT_2``, ``BACKGROUND_1``, ``DARK_1``, ``LIGHT_2``
    - a theme color with a brightness modifier, like ``ACCENT_1+40``, which is 40% brighter than
      Accent 1, or ``ACCENT_2-20`` which is 20% darker than Accent 2
    - ``'none'`` clears the color, i.e. makes it transparent
    '''
    fill.solid()
    if val == 'none':
        fill.background()
    elif isinstance(val, (list, tuple)):
        fill.fore_color.rgb = RGBColor(*val[:3])
    elif isinstance(val, str):
        val = color_map.get(val, val).upper()
        if val.startswith('#'):
            if len(val) == 7:
                fill.fore_color.rgb = RGBColor.from_string(val[1:])
            elif len(val) == 4:
                fill.fore_color.rgb = RGBColor.from_string(val[1] * 2 + val[2] * 2 + val[3] * 2)
        elif val.startswith('RGB('):
            parts = re.findall(r'\d+', val)
            fill.fore_color.rgb = RGBColor(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            match = theme_color.match(val)
            if match:
                theme = match.group(1) + ('_' + match.group(2) if match.group(2) else '')
                fill.fore_color.theme_color = getattr(MSO_THEME_COLOR, theme)
                if match.group(3):
                    fill.fore_color.brightness = float(match.group(3)) / 100
                # else: No brightness adjustment required
            else:
                raise ValueError('Invalid color: %r' % val)


def fill_opacity(fill: FillFormat, val: Union[int, float, None]) -> None:
    '''Set the FillFormat opacity to a number'''
    if fill.type != MSO_FILL.SOLID:
        raise ValueError('Cannot set opacity: %r on non-solid fill type %r' % (val, fill.type))
    for tag in ('hslClr', 'sysClr', 'srgbClr', 'prstClr', 'scrgbClr', 'schemeClr'):
        color = fill._xPr.find('.//' + qn('a:%s' % tag))
        if color is not None:
            alpha = color.find(qn('a:alpha'))
            if alpha is None:
                alpha = OxmlElement('a:alpha')
                color.append(alpha)
            alpha.set('val', ST_Percentage.convert_to_xml(val))
            break


# Other unit conversions
# ---------------------------------------------------------------------
def binary(val: Union[str, int, float]) -> bool:
    '''Convert string to boolean'''
    if val in {'y', 'yes', 'true', 'Y', 'Yes', 'YES', 'True', 'TRUE', 1, 1.0, True}:
        return True
    if val in {'n', 'no', 'false', 'N', 'No', 'NO', 'False', 'FALSE', 1, 1.0, False}:
        return False
    raise ValueError('Invalid boolean: %r' % val)


def alignment(val: str) -> EnumValue:
    '''Convert string to alignment value'''
    alignment = getattr(PP_ALIGN, val.upper(), None)
    if alignment is not None:
        return alignment
    raise ValueError('Invalid alignment: %s' % val)


# Basic command methods
# ---------------------------------------------------------------------
def name(shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        shape.name = val


def print_command(shape, spec, data: dict):
    spec = spec if isinstance(spec, (list, tuple)) else [spec]
    for item in spec:
        print('    %s: %s' % (item, expr(item, data)))


# Position & style commands
# ---------------------------------------------------------------------
def set_size(prop, method, incr, shape, spec, data: dict):
    '''Generator for top, left, width, height, move-top, move-left, add-width, add-height'''
    val = expr(spec, data)
    if val is not None:
        setattr(shape, prop, method(val) + (getattr(shape, prop) if incr else 0))
        flatten_group_transforms(shape)


def flatten_group_transforms(shape, x=0, y=0, sx=1, sy=1):
    '''
    Groups re-scale child shapes. So changes to size and position of child have unexpected results.
    To avoid this, ensure child rect (a:chOff, a:chExt) is same as group rect (a:off, a:ext).
    See https://stackoverflow.com/a/56485145/100904
    '''
    if isinstance(shape, pptx.shapes.group.GroupShape):
        # Get group and child rect shapes
        xfrm = shape.element.find(qn('p:grpSpPr')).find(qn('a:xfrm'))
        off, ext = xfrm.find(qn('a:off')), xfrm.find(qn('a:ext'))
        choff, chext = xfrm.find(qn('a:chOff')), xfrm.find(qn('a:chExt'))
        # Calculate how much the child rect is transformed from the group rect
        tsx = sx * ext.cx / chext.cx
        tsy = sy * ext.cy / chext.cy
        tx = x + sx * (off.x - choff.x * ext.cx / chext.cx)
        ty = y + sy * (off.y - choff.y * ext.cy / chext.cy)
        # Transform child shapes using (x, y, sx, sy)
        for subshape in shape.shapes:
            flatten_group_transforms(subshape, tx, ty, tsx, tsy)
    # Transform shape positions using (x, y, sx, sy). But get all values before setting.
    # Placeholders need this: https://stackoverflow.com/a/49306814/100904
    left, top = int(shape.left * sx + x + 0.5), int(shape.top * sy + y + 0.5)
    width, height = int(shape.width * sx + 0.5), int(shape.height * sy + 0.5)
    shape.left, shape.top, shape.width, shape.height = left, top, width, height
    # Set child rect coords same as group rect (AFTER scaling the group)
    if isinstance(shape, pptx.shapes.group.GroupShape):
        choff.x, choff.y, chext.cx, chext.cy = off.x, off.y, ext.cx, ext.cy


def zoom(shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        val = float(val)
        shape.left -= int((val - 1) * shape.width / 2)
        shape.top -= int((val - 1) * shape.height / 2)
        shape.width = int(shape.width * val)
        shape.height = int(shape.height * val)


def set_color(prop, attr, shape, spec, data: dict):
    '''Generator for fill, stroke commands'''
    val = expr(spec, data)
    if val is not None:
        fill_color(objectpath(shape, attr), val)


def set_opacity(prop, attr, shape, spec, data: dict):
    '''Generator for fill-opacity, stroke-opacity commands'''
    val = expr(spec, data)
    if val is not None:
        fill_opacity(objectpath(shape, attr), val)


def stroke_width(shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        shape.line.width = length(val)


def set_adjustment(index, shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        shape.adjustments[index] = val


# Link commands
# python-pptx can't set slide links on runs, nor tooltips. Make our own
# ---------------------------------------------------------------------
def get_or_add_link(shape, type, event):
    # el is the lxml element of the shape. Can be ._element or ._run
    el = getattr(shape, conf['link-attrs'][type]['el'])
    # parent is the container inside which we insert the link. Can be p:cNvPr or a:rPr
    parent = el.find('.//' + conf['link-attrs'][type]['tag'], _nsmap)
    # Create link if required. (Else preserve all attributes one existing link, like tooltip)
    link = parent.find(qn('a:%s' % event))
    if link is None:
        link = OxmlElement('a:%s' % event)
        parent.insert(0, link)
    return link


def set_link(type, event, prs, slide, shape, val):
    if val is None:
        return
    link = get_or_add_link(shape, type, event)
    # Set link's r:id= and action= based on the type of the link
    if val in conf['link-action']:                  # it's a ppaction://
        rid = link.get(qn('r:id'), None)
        if rid in slide.part.rels:
            slide.part.drop_rel(rid)
        link.set(qn('r:id'), '')
        link.set('action', conf['link-action'][val])
    elif isinstance(val, int) or val.isdigit():     # it's a slide
        slide_part = prs.slides[int(val) - 1].part
        link.set(qn('r:id'), slide.part.relate_to(slide_part, RT.SLIDE, False))
        link.set('action', 'ppaction://hlinksldjump')
    elif urlparse(val).netloc:                      # it's a URL
        link.set(qn('r:id'), slide.part.relate_to(val, RT.HYPERLINK, True))
        link.attrib.pop('action', '')
    elif os.path.splitext(val)[-1].lower() in conf['link-ppt-files']:   # it's a PPT
        link.set(qn('r:id'), slide.part.relate_to(val, RT.HYPERLINK, True))
        link.set('action', 'ppaction://hlinkpres?slideindex=1&slidetitle=')
    else:                                           # it's a file
        link.set(qn('r:id'), slide.part.relate_to(val, RT.HYPERLINK, True))
        link.set('action', 'ppaction://hlinkfile')
    return link


def set_tooltip(type, prs, slide, shape, val):
    if val is None:
        return
    link = get_or_add_link(shape, type, 'hlinkClick')
    rid, action = link.get(qn('r:id'), None), link.get('action', None)
    # Note: link was just created, or has no action, we can't set a tooltip. So create a next: link
    if rid is None or action is conf['link-action']['noaction']:
        link = set_link(type, 'hlinkClick', prs, slide, shape, 'next')
    link.set('tooltip', val)
    # PS: link: back doesn't work with tooltip


# Text commands
# ---------------------------------------------------------------------
def get_elements(children: List[Union[str, HtmlElement]], element_builder):
    '''
    Convert head & tail text into specified tag, so that we can just process all text and elements
    as a single list.
    '''
    for e in children:
        if isinstance(e, HtmlElement):
            tail = e.tail.rstrip() if e.tail else e.tail
            if e.text or list(e):
                e.tail = ''
                yield e if e.tag == element_builder.args[0] else element_builder(e)
            if tail:
                yield element_builder(tail)
        elif isinstance(e, str):
            if e:
                yield element_builder(e.rstrip())


def baseline(run, val, data):
    if isinstance(val, str):
        val = val.strip().lower()
        # See https://github.com/scanny/python-pptx/pull/601 for unit values
        val = (0.3 if val.startswith('sup') else    # noqa
               -0.25 if val.startswith('sub') else  # noqa
               ST_Percentage._convert_from_percent_literal(val))
    run.font._rPr.set('baseline', ST_Percentage.convert_to_xml(val))


def strike(run, val, data):
    val = ('sngStrike' if val.startswith('s') else
           'dblStrike' if val.startswith('d') else
           'noStrike' if val.startswith('n') else val)
    run.font._rPr.set('strike', val)


para_attr_method = {
    'align': assign(alignment, 'alignment'),
    'bold': assign(binary, 'font', 'bold'),
    'color': lambda p, v, d: fill_color(p.font.fill, v),
    'font-name': assign(str, 'font', 'name'),
    'font-size': assign(length, 'font', 'size'),
    'italic': assign(binary, 'font', 'italic'),
    'level': assign(int, 'level'),
    'line-spacing': assign(length, 'line_spacing'),
    'space-after': assign(length, 'space_after'),
    'space-before': assign(length, 'space_before'),
    'underline': assign(binary, 'font', 'underline'),
}
run_attr_method = {
    'baseline': baseline,
    'bold': assign(binary, 'font', 'bold'),
    'color': lambda r, v, d: fill_color(r.font.fill, v),
    'font-name': assign(str, 'font', 'name'),
    'font-size': assign(length, 'font', 'size'),
    'hover': lambda r, v, d: set_link('text', 'hlinkMouseOver', d['prs'], d['slide'], r, v),
    'italic': assign(binary, 'font', 'italic'),
    'link': lambda r, v, d: set_link('text', 'hlinkClick', d['prs'], d['slide'], r, v),
    'strike': strike,
    'tooltip': lambda r, v, d: set_tooltip('text', d['prs'], d['slide'], r, v),
    'underline': assign(binary, 'font', 'underline'),
}


def text(shape, spec, data):
    '''Set text on shape. Allows paragraph and run formatting with a HTML-like syntax'''
    val = expr(spec, data)
    if val is None:
        return
    if not shape.has_text_frame:
        raise ValueError('Cannot add text to shape %s that has no text frame' % shape.name)
    # Delete all but the first para (required), and its first run (to preserve formatting).
    # All new paras and runs get the same formatting as the first para & run, by default
    frame = shape.text_frame
    for p in frame.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    for r in frame.paragraphs[0].runs[1:]:
        r._r.getparent().remove(r._r)
    para = frame.paragraphs[0]
    para_defaults = para._pPr.attrib
    run_defaults = para.runs[0].font._rPr.attrib if len(para.runs) > 0 else {}
    # Apply the text formatting
    tree = fragments_fromstring(str(val))
    for i, para in enumerate(get_elements(tree, builder.P)):
        # The first para is guaranteed to exist. After that, add a para
        p = frame.add_paragraph() if i >= len(frame.paragraphs) else frame.paragraphs[i]
        # Ensure that all paras have the same alignment, spacing, etc as the first para
        p._pPr.attrib.update(para_defaults)
        # Set specified para attributes
        for attr, val in para.attrib.items():
            if attr in para_attr_method:
                para_attr_method[attr](p, val, data)
        for j, run in enumerate(get_elements([para.text] + list(para), builder.A)):
            # The first run MAY exist, if there was text. Or not. Create if required
            r = p.add_run() if j >= len(p.runs) else p.runs[j]
            # Ensure that all runs have the same color, font, etc as the first run (if any)
            r.font._rPr.attrib.update(run_defaults)
            # Set specified run attributes
            r.text = run.text
            for attr, val in run.attrib.items():
                if attr in run_attr_method:
                    run_attr_method[attr](r, val, data)


def replace(shape, spec, data):
    if not isinstance(spec, dict):
        raise ValueError('replace: needs a dict of {old: new} text, not %r' % spec)
    if not shape.has_text_frame:
        raise ValueError('Cannot add text to shape %s that has no text frame' % shape.name)

    def insert_run_after(r, p, original_r):
        new_r = copy.deepcopy(original_r)
        r._r.addnext(new_r)
        return _Run(new_r, p)

    spec = {re.compile(old): fragments_fromstring(expr(new, data)) for old, new in spec.items()}
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            for old, tree in spec.items():
                match = old.search(r.text)
                if match:
                    original_r, prefix, suffix = r._r, r.text[:match.start()], r.text[match.end():]
                    if prefix:
                        r.text = prefix
                        r = insert_run_after(r, p, original_r)
                    for j, run in enumerate(get_elements(tree, builder.A)):
                        r = insert_run_after(r, p, original_r) if j > 0 else r
                        r.text = run.text
                        for attr, val in run.attrib.items():
                            if attr in run_attr_method:
                                run_attr_method[attr](r, val, data)
                    if suffix:
                        # Ensure suffix has same attrs as original text
                        r = insert_run_after(r, p, original_r)
                        r.text = suffix


def set_text(attr, on_para, shape, spec, data):
    '''Generator for bold, italic, color, and other text commands'''
    val = expr(spec, data)
    if val is not None:
        if not shape.has_text_frame:
            raise ValueError('Cannot change text of shape %s that has no text frame' % shape.name)
        # If on_para=True, set attr on every para, clear attr on every run (e.g. bold, italic)
        # Else, set attr on every run, clear attr on every para (e.g. color)
        para_method, run_method = para_attr_method[attr], run_attr_method[attr]
        for para in shape.text_frame.paragraphs:
            para_method(para, val if on_para else None, data)
            for run in para.runs:
                run_method(run, None if on_para else val, data)


# Image commands
# ---------------------------------------------------------------------

def image(shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        rid = shape._pic.blipFill.blip.rEmbed
        part = shape.part.related_parts[rid]
        if urlparse(val).netloc:
            part._blob = requests.get(val).content
        else:
            part._blob = gramex.cache.open(val, 'bin')
        # Preserve aspect ratio and width. Adjust height
        img = Image.open(io.BytesIO(part._blob))
        img_width, img_height = img.size
        shape.height = int(shape.width * img_height / img_width)


def image_width(shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        val = length(val)
        shape.width, shape.height = val, int(val * shape.height / shape.width)


def image_height(shape, spec, data: dict):
    val = expr(spec, data)
    if val is not None:
        val = length(val)
        shape.width, shape.height = int(val * shape.width / shape.height), val


cmdlist = {
    # Basic commands
    'name': name,
    'print': print_command,
    # Position
    'top': partial(set_size, 'top', length, False),
    'left': partial(set_size, 'left', length, False),
    'width': partial(set_size, 'width', length, False),
    'height': partial(set_size, 'height', length, False),
    'rotation': partial(set_size, 'rotation', float, False),
    'add-top': partial(set_size, 'top', length, True),
    'add-left': partial(set_size, 'left', length, True),
    'add-width': partial(set_size, 'width', length, True),
    'add-height': partial(set_size, 'height', length, True),
    'add-rotation': partial(set_size, 'rotation', float, True),
    # Shape
    'zoom': zoom,
    'adjustment1': partial(set_adjustment, 0),
    'adjustment2': partial(set_adjustment, 1),
    'adjustment3': partial(set_adjustment, 2),
    'adjustment4': partial(set_adjustment, 3),
    # Style
    'fill': partial(set_color, 'fill', 'fill'),
    'stroke': partial(set_color, 'stroke', 'line.fill'),
    'fill-opacity': partial(set_opacity, 'fill-opacity', 'fill'),
    'stroke-opacity': partial(set_opacity, 'stroke-opacity', 'line.fill'),
    'stroke-width': stroke_width,
    # Image
    'image': image,
    'image-width': image_width,
    'image-height': image_height,
    # Link
    'link': lambda shape, spec, data: (
        set_link('shape', 'hlinkClick', data['prs'], data['slide'], shape, expr(spec, data))),
    'hover': lambda shape, spec, data: (
        set_link('shape', 'hlinkHover', data['prs'], data['slide'], shape, expr(spec, data))),
    'tooltip': lambda shape, spec, data: (
        set_tooltip('shape', data['prs'], data['slide'], shape, expr(spec, data))),
    # Text
    'replace': replace,
    'text': text,
    'bold': partial(set_text, 'bold', True),
    'color': partial(set_text, 'color', False),         # "False" to set color on runs not paras
    'font-name': partial(set_text, 'font-name', True),
    'font-size': partial(set_text, 'font-size', True),
    'italic': partial(set_text, 'italic', True),
    'underline': partial(set_text, 'underline', True),
    # Others
    # 'chart': chart,
    # 'table': table,
    # Custom charts
    # 'sankey': sankey,
    # 'bullet': bullet,
    # 'treemap': treemap,
    # 'heatgrid': heatgrid,
    # 'calendarmap': calendarmap,
}
