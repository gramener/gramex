/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-html',
  template: /* HTML */`
  <%= value %>
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  properties: fields['bs4-html']
})
