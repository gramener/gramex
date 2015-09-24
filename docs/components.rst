Components
----------

`Web components`_ allow custom HTML elements. With a small `polyfill`_, target
browsers are supported.

.. _Web components: http://webcomponents.org/
.. _polyfill: https://github.com/WebComponents/webcomponentsjs


Layered data-driven approach

- Composable components. Apply a component over another in a way
- Scaling and other transformations
- Axes
- Default stroke colour, stroke width, padding, etc
- Attribute lambda parameters
- Transformable. Transforms should also be composable.
- Ability to access template intermediate variables (layouts, scales,
  etc) from outside on server and client side
- Themes
- Any symbol instead of default symbols

Flexible rendering:

- Rendering may be on the client side or the server side
- Rendered views can be edited on the client side as well
- Renderable for PPTX, PDF, PNG, SVG, etc
- Responsive on the server side (re-layout) or the client side
  (preserve aspect)
- CSS classes reserved for components

Containers and controls:

- Grids
- Themes
- Standard components

Interactive charts:

- Animated transitions
- Cross-filter like filtering
- How will we incorporate dynamic interactive controls?
- Interactivity involves 3 things (We need a catalogue of all of these):
    - Events / components (brushing, clicking, sliding, etc)
    - Actions (filter, zoom-in, etc)
    - Combinations (click-to-filter, etc)

Intelligence:

-  Automated colour contrast
-  Automated placement of legends
-  Automated placement of labels
-  Automated placement of annotations
-  Text wrapping and fitting

Support

-  IPython Notebooks

