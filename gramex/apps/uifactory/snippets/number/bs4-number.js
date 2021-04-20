/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-number',
  template: /* HTML */`
  <style>
    bs4-number {
      display: block;
    }
  </style>
  <label data-type="number" for="<%= name %>"><%= label %></label>
  <input type="number"
    class="form-control" name="<%= name %>" id="<%= name %>" aria-describedby="<%= name %>-help" placeholder="<%= placeholder %>"
    min="<%= min %>" max="<%= max %>" step="<%= step %>" value="<%= value %>">
  <% if (typeof help !== 'undefined' && help.length > 0) { %>
    <small id="number-help" class="form-text text-muted"><%= help %></small>
  <% } %>
  `,
  properties: fields['bs4-number']
})
