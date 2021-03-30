uifactory.register({
  name: 'component-editor',
  template: /* HTML */`<!-- Write the component template -->
  <div class="code">
    <g-text label="Component name" value="<%= name %>"></g-text>
    <resizable-accordion label="template" open>
      <monaco-editor
        language="html"
        theme="vs-dark">
        <code>
          <%= _.escape(template) %>
        </code>
      </monaco-editor>
    </resizable-accordion>
    <resizable-accordion label="usage" open>
      <monaco-editor
        language="html"
        theme="vs-dark">
        <code>
        <% if(usage) { %>
          <%= _.escape(usage) %>
        <% } %>
        </code>
      </monaco-editor>
    </resizable-accordion>
  </div>
  <div class="preview">
    <div class="container">
    </div>
  </div>
  <script>
  function updatePreview(e) {
    const target = e.target.closest('component-editor')
    const container = target.querySelector('.preview > .container')
    container.innerHTML = ''
    const iframe = document.createElement('iframe')
    container.appendChild(iframe)
    const doc = iframe.contentWindow.document
    const template = target
    .querySelector('resizable-accordion[label="template"]  monaco-editor')
    .editor
    .getValue()
    const spec = {
      template: template,
      name: target.querySelector('g-text').value,
      window: iframe.contentWindow
    }
    const previewCode = target.querySelector('resizable-accordion[label="usage"]  monaco-editor').editor.getValue()
    doc.open()
    doc.write(previewCode)
    doc.close()
    uifactory.register(spec)
  }
  on('value-change', 'component-editor yaml-editor', updatePreview)
  on('input', 'component-editor monaco-editor *', updatePreview)
  on('prop-edit', 'component-editor  prop-editor', updatePreview)
  on('render', 'component-editor', function(e) {
    Promise.all(Array.from(e.target.querySelectorAll('monaco-editor')).map(el => new Promise(res => {
      const interval = setInterval(_ => {
        if('editor' in el) {
          clearInterval(interval)
          res()
        }
      }, 100)
    })))
    .then(_ => updatePreview(e))
  }, { matchTarget: true, once: true })
  </script>
  <style>
  component-editor {
    display: flex;
    width: 100%;
  }
  component-editor .code {
    width: 50%;
    resize: horizontal;
    padding-left: 0.25rem;
  }
  component-editor .preview {
    width: 50%;
  }
  component-editor resizable-accordion {
    display: block;
    margin-top: 0.5rem;
  }
  component-editor resizable-accordion monaco-editor {
    display: block;
    height: calc(50vh - 4.5rem);
  }
  .preview {
    display: flex;
    flex-direction: column;
  }
  .preview > * {
    flex: 1;
    height: 50%;
    overflow-y: auto;
  }
  monaco-editor .overflowingContentWidgets {
    display: none;
  }
  </style>
  `,
  options: [
    {
      name: 'name',
      value: 'g-component'
    },
    {
      name: 'properties',
      value: '[]'
    },
    {
      name: 'template',
      value: '<h1>Hello</h1>'
    },
    {
      name: 'usage',
      value: '<g-component></g-component>'
    }
  ]
})