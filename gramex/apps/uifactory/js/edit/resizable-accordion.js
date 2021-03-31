/* globals uifactory */

uifactory.register({
  name: 'resizable-accordion',
  template: /* HTML */`<!-- Write the component template -->
  <style>
  resizable-accordion > details > summary::marker {
    content: ''
  }
  resizable-accordion > details[open] > summary > button {
    filter: brightness(70%) contrast(120%);
    border-radius: 0.2rem 0.2rem 0 0;
  }
  resizable-accordion > details > main > * {
    resize: vertical;
    overflow-y: auto;
    overflow-x: hidden;
  }
  </style>
  <% if(open !== null) { %>
  <details open>
  <% } else { %>
  <details>
  <% } %>
    <summary>
      <button type="button" class="btn btn-secondary" data-toggle="button" aria-pressed="false">
        <%= label %>
      </button>
    </summary>
    <main>
      <%= this.innerHTML %>
    </main>
  </details>
  <script>
  /* globals on */

  on('click', 'resizable-accordion > details > summary > button', function(e) {
    const resizableAccordion = e.target.parentElement.parentElement.parentElement
    if(resizableAccordion.hasAttribute('open')) {
      resizableAccordion.removeAttribute('open')
    } else {
      resizableAccordion.setAttribute('open', '')
    }
  })
  </script>
  `,
  options: [
    {
      name: 'label',
      value: 'toggle'
    },
    {
      name: 'open',
      value: null
    }
  ]
})
