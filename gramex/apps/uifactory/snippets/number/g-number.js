uifactory.register({
  name: 'g-number',
  template: /* HTML */`
  <style>
    g-number {
      display: block;
    }
  </style>
  <label data-type="number" for="<%= name %>"><%= label %></label>
  <input type="number"
    class="form-control" name="<%= name %>" id="<%= name %>" aria-describedby="<%= name %>-help" placeholder="<%= placeholder %>"
    min="<%= min %>" max="<%= max %>" step="<%= step %>" value="<%= value %>">
  <% if (typeof help != 'undefined') { %>
    <small id="number-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  options: fields['g-number']
})
