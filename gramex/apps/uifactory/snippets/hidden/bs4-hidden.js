/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-hidden',
  template: /* HTML */`
  <label data-type="html" for="hidden-input"><%= label %></label>
  <input type="hidden" id="<%= name %>" name="<%= name %>" value="<%= value %>">
  `,
  properties: fields['bs4-hidden']
})
