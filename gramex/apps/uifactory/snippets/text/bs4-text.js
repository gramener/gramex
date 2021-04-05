/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-text',
  template: /* HTML */`
  <style>
    bs4-text {
      display: block;
    }
  </style>
  <label data-type="text" for="<%= name %>"><%= label %></label>
  <% let id = typeof this.id !== undefined ? this.id : Date.now() %>
  <input type="text" class="form-control" name="<%= name %>" id="bs4-<%= id %>" aria-describedby="text-<%= name %>" placeholder="<%= placeholder %>" value="<%= value %>">
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  properties: fields['bs4-text']
})
