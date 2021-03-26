(function() {
  const templateString = /* HTML */`
  <style>
    g-textarea {
      display: block;
    }
  </style>
  <template component=""
    label="Textarea"
    placeholder="Placeholder"
    value=""
    name="textarea-input"
    help=""
    rows="3"
  >

  </template>
  `
  const template = document.createRange().createContextualFragment(templateString)
  document.body.appendChild(template)
  })()
  createComponent({
    name: 'g-textarea',
    template: /* HTML */`
    <style>
      g-textarea {
        display: block;
      }
    </style>
    <label data-type="textarea" for="<%= name %>"><%= label %></label>
    <textarea class="form-control" name="<%= name %>" id="<%= name %>" rows="<%= rows %>" placeholder="<%= placeholder %>"><%= value %></textarea>
    <% if (typeof help != 'undefined') { %>
      <small id="text-input-help" class="form-text text-muted"><%= help %></small>
    <% } %>
    `,
    options: fields['g-textarea']
  })