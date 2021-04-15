/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-radio',
  template: /* HTML */`
  <script type="text/html">
    <label data-type="text" for="<%= name %>"><%= label %></label>
    <% let _options = options.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) %>
    <% _options.map(item => item.trim()).forEach(function (option, ind) { %>
      <% let local_id = generate_id() %>
      <div class="form-check py-2 px-0">
        <input type="radio" class="px-2" name="<%= name %>" id="<%= local_id %>" value='<%= encodeURI(option) %>'
          <%= value === option ? "checked" : "" %>>
        <label data-type="radio" class="px-2" for="<%= local_id %>">
          <%= option %>
        </label>
        <% if (typeof help != 'undefined' && ind === options.split(',').map(item => item.trim()).length - 1) { %>
          <small id="text-input-help" class="form-text text-muted"><%= help %></small>
        <% } %>
      </div>
    <% }) %>
  </script>
  `,
  properties: fields['bs4-radio']
})
