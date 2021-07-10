/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-multiselect',
  template: /* HTML */`
<style>
  @import url('https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.18/dist/css/bootstrap-select.min.css');
  /* selectpicker styles */
bs4-multiselect {
  display: inline-block;
}
bs4-multiselect span.text:before {
  content: '';
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background-color: #E6E6E6;
  position: absolute;
  left: 17px;
  top:8px;
}

bs4-multiselect .bs-ok-default:after {
  border-style:none !important;
}

bs4-multiselect .show-tick .dropdown-menu .selected span.check-mark {
  background-color: #25B8FF;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  left: 17px;
  z-index: 10;
  top: 8px !important;
}
bs4-multiselect .dropdown-item.active, bs4-multiselect .dropdown-item:active{
  background-color:transparent !important;
}
/* It is generated dynamically, we are not allowing add default-classes in html. */
bs4-multiselect .dropdown-menu{
  border: 1px solid rgba(151,151,151,0.42);
  border-radius: 8px;
  padding-right:3px;
  padding-left:3px;
  background-color: #FFFFFF;
  box-shadow: 0 12px 14px 0 rgba(0,0,0,0.04);
  left: auto !important;
  right: 0;
  min-width:108px;
}
bs4-multiselect .bs-actionsbox, .bs-donebutton, .bs-searchbox{
  padding:0px;
}
/* select title header */
bs4-multiselect .popover-header{
  text-align:center;
  font-size:14px;
  font-weight:600;
  border-bottom:1px solid rgba(151, 151, 151, 0.27);
  margin-bottom:8px;
}
bs4-multiselect .popover-header button,
bs4-multiselect ul .apply-button-group{
  display:none;
}
bs4-multiselect .dropdown-menu.inner{
  max-height:150px;
}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap-select/1.13.18/js/bootstrap-select.min.js"></script>
<script type="text/html">
  <label class="d-block" data-type="select" for="select-element"><%= label %></label>
  <select class="selectpicker" multiple name="<%= name %>" id="<%= name %>">
    <% if (typeof options !== undefined) { %>
      <% let _options = split_options(options) || [] %>
      <%= _options.map(item => item.trim()).map((opt) => {
        var selected = opt === value ? "selected" : "";
        return '<option class="text-dark pb-1 pl-5"' + selected + ' value="' + encodeURI(opt) + '">' + opt + '</option>'
      }).join('') %>
    <% } %>
    <% [...this.children].forEach(child => { %>
      <% if (child.tagName === 'OPTION' ) { %>
        <%= child.outerHTML %>
      <% } %>
    <% }) %>
  </select>
  <% if (typeof help != 'undefined') { %>
    <small id="text-input-help" class="form-text text-muted"><%= help %></small>
  <% } %>
</script>
<script>
  $.fn.selectpicker.Constructor.BootstrapVersion = '4';
  document.body.addEventListener('render', function (e) {
    // select element -> element should be e.target
    // button -> select attributes -- element should be this
    if(!e.target.matches('bs4-multiselect')) return
    const opts = Object.assign({}, e.target.__model)
    const attrs = {}
    const dataset = {}
    const bsSelectAttributes = ["title", "multiple", "value", "actionsBox", "deselectAllText", "header", "liveSearch", "liveSearchPlaceholder", "liveSearchStyle", "selectAllText", "size", "style", "title"];
    const dataAttr = ["actionsBox", "deselectAllText", "header", "liveSearch", "liveSearchPlaceholder", "liveSearchStyle", "selectAllText", "size", "style", "title"];
    const select = e.target.querySelector('select')
    Object.keys(opts).forEach(key => {
      if(!bsSelectAttributes.includes(key)) {
        delete opts[key]
      } else {
        if(dataAttr.includes(key)) {
          select.dataset[key] = opts[key]
        } else {
          attrs[key] = opts[key]
        }
      }
    })
    $(select).attr(opts);
    $(select).selectpicker();
  })
</script>
`,
properties: fields['bs4-multiselect']
})
