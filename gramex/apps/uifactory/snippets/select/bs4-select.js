/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-select',
  template: /* HTML */`
<style>
  @import url('https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.18/dist/css/bootstrap-select.min.css');
  /* selectpicker styles */
bs4-select {
  display: inline-block;
}
bs4-select span.text:before {
  content: '';
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background-color: #E6E6E6;
  position: absolute;
  left: 17px;
  top:8px;
}

bs4-select .bs-ok-default:after {
  border-style:none !important;
}

bs4-select .show-tick .dropdown-menu .selected span.check-mark {
  background-color: #25B8FF;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  left: 17px;
  z-index: 10;
  top: 8px !important;
}
bs4-select .dropdown-item.active, bs4-select .dropdown-item:active{
  background-color:transparent !important;
}
/* It is generated dynamically, we are not allowing add default-classes in html. */
bs4-select .dropdown-menu{
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
bs4-select .bs-actionsbox, .bs-donebutton, .bs-searchbox{
  padding:0px;
}
/* select title header */
bs4-select .popover-header{
  text-align:center;
  font-size:14px;
  font-weight:600;
  border-bottom:1px solid rgba(151, 151, 151, 0.27);
  margin-bottom:8px;
}
bs4-select .popover-header button,
bs4-select ul .apply-button-group{
  display:none;
}
bs4-select .dropdown-menu.inner{
  max-height:150px;
}
</style>
<script src="https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.18/dist/js/bootstrap-select.min.js"></script>
<script type="text/html">
  <label class="d-block" data-type="select" for="select-element"><%= label %></label>
  <select class="selectpicker" name="<%= name %>" id="<%= name %>">
    <% if (typeof options !== undefined) { %>
      <%= options.split(', ').map((opt) => {
        var selected = opt === value ? "selected" : "";
        return '<option class="text-dark pb-1 pl-5"' + selected + ' value="' + opt + '">' + opt + '</option>'
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
    if(!e.target.matches('bs4-select')) return
    const opts = Object.assign({}, this._options)
    const bsSelectAttributes = ["title", "multiple", "value", "data-actions-box","data-container","data-count-selected-text","data-deselect-all-text","data-dropdown-align-right","data-dropup-auto","data-header","data-hide-disabled","data-icon-base","data-live-search","data-live-search-normalize","data-live-search-placeholder","data-live-search-style","data-max-options","data-max-options-text","data-mobile","data-multiple-separator","data-none-selected-text","data-none-results-text","data-select-all-text","data-selected-text-format","data-select-on-tab","data-show-content","data-show-icon","data-show-subtext","data-show-tick","data-size","data-style","data-style-base","data-tick-icon","data-title","data-virtual-scroll","data-width","data-window-padding"];
    Object.keys(opts).forEach(key => {
      if(!bsSelectAttributes.includes(key)) {
        delete opts[key]
      }
    })
    $(e.target.querySelector('select')).attr(opts);
    $(e.target.querySelector('select')).selectpicker();
  })
</script>
`,
properties: fields['bs4-select']
})
