uifactory.register({
  name: 'g-range',
  template: /* HTML */`
  <style>
    g-range {
      display: block;
    }
  </style>
  <label data-type="range" for="<%= name %>"><%= label %></label>
  <input type="range" class="form-control-range" id="<%= name %>"
  min="<%= min %>" max="<%= max %>" step="<%= step %>" value="<%= value %>">
  `,
  options: fields['g-range']
})
