/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-select',
  template: /* HTML */`
<script type="text/html">
  <label class="d-block" data-type="select" for="<%= name %>"><%= label %></label>
  <select class="custom-select" name="<%= name %>" id="<%= name %>">
    <% if (typeof options !== undefined || options !== null) { %>
      <% let _options = split_options(options) || [] %>
      <%= _options.map(item => item.trim()).map((opt) => {
        var selected = opt === value ? "selected" : ""
        return '<option ' + selected + ' value="' + encodeURI(opt) + '">' + opt + '</option>'
      }).join('') %>
    <% } %>
    <% [...this.children].forEach(child => { %>
      <% if (child.tagName === 'OPTION' ) { %>
        <%= child.outerHTML %>
      <% } %>
    <% }) %>
  </select>
  <% if (typeof help !== 'undefined' && help.length > 0) { %>
    <small id="text-input-help" class="d-block text-muted"><%= help %></small>
  <% } %>
</script>
<script>
  document.body.addEventListener('render', function (e) {
    if(!e.target.matches('bs4-select')) return
    const opts = Object.assign({}, e.target.__model)
    const bsSelectAttributes = ["title", "value"]
    const select = this.querySelector('select')
    Object.keys(opts).forEach(key => {
      if(!bsSelectAttributes.includes(key)) {
        delete opts[key]
      }
    })
    $(e.target.querySelector('select')).attr(opts);
  })
</script>
`,
properties: fields['bs4-select']
})
