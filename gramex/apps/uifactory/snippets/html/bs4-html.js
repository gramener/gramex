/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-html',
  template: /* HTML */`
  <label data-type="html" for="<%= name %>"><%= label %></label>
  <%= value %>
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  properties: fields['bs4-html']
})
