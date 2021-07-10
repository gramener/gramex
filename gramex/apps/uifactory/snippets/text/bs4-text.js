/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-text',
  template: /* HTML */`
  <style>
    bs4-text {
      display: block;
    }
  </style>
  <script type="text/html">
    <label data-type="text" for="<%= name %>"><%= label %></label>
    <% let id = typeof this.id !== undefined || this.id.length > 0 ? this.id : Date.now() %>
    <input type="text" class="form-control" name="<%= name %>" id="bs4-<%= id %>" aria-describedby="text-<%= name %>" placeholder="<%= typeof placeholder !== undefined && placeholder.length > 0 ? placeholder : '' %>" value="<%= value.length > 0 ? replace_double(decodeURIComponent(value)) : '' %>">
    <% if (typeof help !== 'undefined' && help.length > 0) { %>
      <small id="text-input-help" class="form-text text-muted"><%= help %></small>
    <% } %>
  </script>
  `,
  properties: fields['bs4-text']
})
