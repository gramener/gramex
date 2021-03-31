/* globals uifactory, fields */

uifactory.register({
  name: 'g-text',
  template: /* HTML */`
  <style>
    g-text {
      display: block;
    }
  </style>
  <label data-type="text" for="<%= name %>"><%= label %></label>
  <% let id = typeof this.id !== undefined ? this.id : Date.now() %>
  <input type="text" class="form-control" name="<%= name %>" id="g-<%= id %>" aria-describedby="text-<%= name %>" placeholder="<%= placeholder %>" value="<%= value %>">
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  options: fields['g-text']
})
