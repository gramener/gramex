/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-checkbox',
  template: /* HTML */`
  <script type="text/html">
    <label data-type="text" for="<%= name %>"><%= label %></label>
    <% let _options = split_options(options) %>
    <% _options.map(item => item.trim()).forEach(function (option, ind) { %>
      <% let values = split_options(value).map(item => item.trim()) %>
      <% let local_id = generate_id() %>
      <div class="form-check p-0">
        <input type="checkbox" class="px-2" name="<%= name %>" id="<%= ind + '-' + local_id %>" value='<%= encodeURI(option) %>'
          <%= values.indexOf(option) > -1 ? "checked" : "" %> >
        <label data-type="checkbox" class="px-2" for="<%= ind + '-' + local_id %>">
          <%= option %>
        </label>
        <% if (typeof help != 'undefined' && ind === _options.map(item => item.trim()).length - 1) { %>
          <small id="text-input-help" class="form-text text-muted"><%= help %></small>
        <% } %>
      </div>
    <% }) %>
  </script>
  `,
  properties: fields['bs4-checkbox']
})
