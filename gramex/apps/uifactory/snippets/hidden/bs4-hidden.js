/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-hidden',
  template: /* HTML */`
  <input type="hidden" id="<%= name %>" name="<%= name %>" value="<%= value %>">
  `,
  properties: fields['bs4-hidden']
})
