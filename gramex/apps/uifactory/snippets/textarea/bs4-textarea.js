/* globals uifactory, fields */

(function() {
  const templateString = /* HTML */`
  <style>
    bs4-textarea {
      display: block;
    }
  </style>
  <template component="bs4-textarea"
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

uifactory.register({
  name: 'bs4-textarea',
  template: /* HTML */`
  <style>
    bs4-textarea {
      display: block;
    }
  </style>
  <label data-type="textarea" for="<%= name %>"><%= label %></label>
  <textarea class="form-control" name="<%= name %>" id="<%= name %>" rows="<%= rows %>" placeholder="<%= placeholder %>"><%= value %></textarea>
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  properties: fields['bs4-textarea']
})
