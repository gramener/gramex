/* eslint-env es6 */

document.querySelectorAll('template[component], script[type="text/html"][component]').forEach(function(component) {
  // A template like <template component="comp" attr="val">
  // has componentname = "comp" and config.options = {attr: {value: "val", type: "text"}}
  let componentname, options = {}
  for (let attr of component.attributes)
    if (attr.name == 'component')
      componentname = attr.value.toLowerCase()
    else
      options[attr.name] = {
        type: 'text',
        value: attr.value
      }

  // Create the custom component on the current window
  createComponent.call(window, {
    name: componentname,
    // If <template> tag is used unescape the HTML. It'll come through as &lt;tag-name&gt;
    // But if <script> tag is used, no need to unescape it.
    template: component.tagName.toLowerCase() == 'template' ? _.unescape(component.innerHTML) : component.innerHTML,
    options: options
  })
})

// createComponent('g-component', { template: '<%= 1 + 2 %>' })
// creates a <g-component> with the lodash template
function createComponent(config) {
  // The custom element is defined on this window
  const _window = this

  // Each window has its own component registry. "this" picks the registry of the current window
  const registry = this.__UIRegistry = this.__UIRegistry || {}
  // If a component is already registered, don't re-register.
  // TODO: Should this be an error or a warning?
  if (config.name in registry)
    return console.warn(`Can't redefine registered component ${config.name}`)
  registry[config.name] = config = Object.assign({ __init: {}, }, config)

  // Compile into lodash template
  const template = _.template(config.template)
  // The keys of options become the observable attrs
  const options = config.options || {};
  // If the template uses any variables that are not defined in options,
  // TRY to add them to options as text with empty string defaults.
  // BUT: If the component uses this.innerHTML or this.children, just ignore exceptions.
  // TODO: Since this is brittle and can easily fail, remove this.
  try {
    template(new Proxy(options, {
      has: (options, prop) => prop.match(/^__/) ? false :
                              options.hasOwnProperty(prop) ? true :
                              prop in _window ? true :
                              options[prop] = { type: 'text', value: '' },
      get: (options, prop) => options[prop] ? options[prop].value : _window[prop]
    }))
  } catch(e) {}

  const attrs = Object.keys(options)

  // Create the custom HTML element
  class UIFactory extends _window.HTMLElement {
    connectedCallback() {
      // TODO: add config to this. Inform Bhanu

      // If style: is specified, append <style>...</style> to window's <head>
      // If script: is specified, append <script>...</script> to window's <body>
      [['style', 'head'], ['script', 'body']].forEach(function([type, target]) {
        if (config[type] && !config.__init[type]) {
          const el = _window.document.createElement(type)
          el.textContent = config[type]
          _window.document[target].appendChild(el)
          config.__init[type] = true
        }
      })

      // Expose attributes as properties
      attrs.forEach(attr => {
        Object.defineProperty(this, attr, {
          get: function () {
            return this.getAttribute(attr)
          },
          set: function (val) {
            this.setAttribute(attr, val)
          }
        })
      })

      // this.__obj holds the object passed to the template.
      // Initialize this.__obj with default values.
      this.__obj = _.mapValues(options, 'value')
      // Override with actual attributes and slots
      for (var i = 0, len = this.attributes.length; i < len; i++)
        this.__obj[this.attributes[i].name] = this.attributes[i].value
      // template can access the component at $target
      this.__obj.$target = this
      // template can access to the original children via "this"
      this.__originalNode = this.cloneNode(true)

      // this.render() re-renders the object based on current options.
      this.render()
    }

    render(config) {
      this.innerHTML = template.call(this.__originalNode, Object.assign(this.__obj, config))
      // Generate a render event on this component for initialization
      this.dispatchEvent(new CustomEvent('render', { bubbles: true }))
    }

    // The list of attributes to watch for changes on is based on the keys of
    // config.options, When any of these change, attributeChangedCallback is called.
    static get observedAttributes() {
      return attrs
    }

    // When any attribute changes, update this.__obj and re-render
    attributeChangedCallback(name, oldValue, newValue) {
      // If the component is not initialized, don't render it
      // If it's intialized, re-render
      if (this.__obj) {
        this.__obj[name] = newValue
        this.render()
      }
    }
  }

  // Use customElements from current window.
  // To use a different window, use createComponent.call(your_window, component)
  _window.customElements.define(config.name, UIFactory)

  // Store the class in the registry for future reference.
  // Do this after customElements.define succeeds -- that allows re-definition on failure.
  registry[config.name].class = UIFactory
}
