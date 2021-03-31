/* globals uifactory, fields */

uifactory.register({
  name: 'g-password',
  template: /* HTML */`
  <label data-type="password" for="<%= name %>"><%= label %></label>
  <input type="password" class="form-control" name="<%= name %>" id="<%= name %>" placeholder="<%= placeholder %>">
  `,
  options: fields['g-password']
})
