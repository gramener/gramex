/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-checkbox',
  template: /* HTML */`
  <label data-type="text" for="<%= name %>"><%= label %></label>
  <% options.split(',').forEach(function (option, ind) { %>
    <div class="form-check p-0">
      <input type="checkbox" class="px-2" name="<%= name %>" id="<%= ind + '-' + option.trim() %>" value="<%= option.trim() %>" <%= value === 'yes' ? "checked" : "" %> >
      <label data-type="checkbox" class="px-2" for="<%= ind + '-' + option.trim() %>">
        <%= option.trim() %>
      </label>
      <% if (typeof help != 'undefined' && ind === options.split(',').length - 1) { %>
        <small id="text-input-help" class="form-text text-muted"><%= help %></small>
      <% } %>
    </div>
  <% }) %>
  `,
  properties: fields['bs4-checkbox']
})
