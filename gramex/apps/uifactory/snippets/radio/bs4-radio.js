/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-radio',
  template: /* HTML */`
  <label data-type="text" for="<%= name %>"><%= label %></label>
  <% options.split(',').forEach(function (option, ind) { %>
    <div class="form-check py-2 px-0">
      <input type="radio" class="px-2" name="<%= name %>" id="<%= option %>" value="<%= option %>" <%= (typeof checked != undefined) ? "checked" : "" %>>
      <label data-type="radio" class="px-2" for="<%= option %>">
        <%= option %>
      </label>
      <% if (typeof help != 'undefined' && ind === options.split(',').length - 1) { %>
        <small id="text-input-help" class="form-text text-muted"><%= help %></small>
      <% } %>
    </div>
  <% }) %>
  `,
  properties: fields['bs4-radio']
})
