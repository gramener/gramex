/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-range',
  template: /* HTML */`
  <style>
    bs4-range {
      display: block;
    }
  </style>
  <label data-type="range" for="<%= name %>"><%= label %></label>
  <input type="range" class="form-control-range" id="<%= name %>"
  min="<%= min %>" max="<%= max %>" step="<%= step %>" value="<%= value %>">
  `,
  properties: fields['bs4-range']
})