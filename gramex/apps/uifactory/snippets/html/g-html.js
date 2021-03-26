createComponent({
  name: 'g-html',
  template: /* HTML */`
  <label data-type="html" for="<%= name %>"><%= label %></label>
  <%= value %>
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  options: fields['g-html']
})