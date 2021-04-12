/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-checkbox',
  template: /* HTML */`
  <script type="text/html">
    <label data-type="text" for="<%= name %>"><%= label %></label>
    <% options.split('|').map(item => item.trim()).forEach(function (option, ind) { %>
      <% let values = value.split('|').map(item => item.trim()) %>
      <div class="form-check p-0">
        <input type="checkbox" class="px-2" name="<%= name %>" id="<%= ind + '-' + option %>" value="<%= option %>"
          <%= values.indexOf(option) > -1 ? "checked" : "" %> >
        <label data-type="checkbox" class="px-2" for="<%= ind + '-' + option %>">
          <%= option %>
        </label>
        <% if (typeof help != 'undefined' && ind === options.split('|').map(item => item.trim()).length - 1) { %>
          <small id="text-input-help" class="form-text text-muted"><%= help %></small>
        <% } %>
      </div>
    <% }) %>
  </script>
  `,
  properties: fields['bs4-checkbox']
})
