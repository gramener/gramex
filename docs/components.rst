Components
----------

Visual components are rendered by default on the DOM as `web components`_ or
custom HTML elements. With a small `polyfill`_, target browsers are supported.

.. _Web components: http://webcomponents.org/
.. _polyfill: https://github.com/WebComponents/webcomponentsjs

Vega is the charting engine of choice, but may not be the only one. (Leaflet
maps, for example, may be an option.)

Components can be rendered on the client side or the server side, in multiple
formats (including PPTX, images, and SVG.)

Components are packaged into a chartogram

- a single Javascript file
- managed by an npm module
- served via github.io (dev) / jsdelivr (prod)



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

