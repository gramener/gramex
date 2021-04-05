/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-password',
  template: /* HTML */`
  <label data-type="password" for="<%= name %>"><%= label %></label>
  <input type="password" class="form-control" name="<%= name %>" id="<%= name %>" placeholder="<%= placeholder %>">
  `,
  properties: fields['bs4-password']
})
