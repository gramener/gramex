$('body').on('render', 'g-select', function (e) {
  const opts = Object.assign({}, this.__obj)
  const bsSelectAttributes = ["title", "multiple", "value", "data-actions-box","data-container","data-count-selected-text","data-deselect-all-text","data-dropdown-align-right","data-dropup-auto","data-header","data-hide-disabled","data-icon-base","data-live-search","data-live-search-normalize","data-live-search-placeholder","data-live-search-style","data-max-options","data-max-options-text","data-mobile","data-multiple-separator","data-none-selected-text","data-none-results-text","data-select-all-text","data-selected-text-format","data-select-on-tab","data-show-content","data-show-icon","data-show-subtext","data-show-tick","data-size","data-style","data-style-base","data-tick-icon","data-title","data-virtual-scroll","data-width","data-window-padding"];
  Object.keys(opts).forEach(key => {
    if(!bsSelectAttributes.includes(key)) {
      delete opts[key]
    }
  })
  $(this.querySelector('select')).attr(opts);
  $(this.querySelector('select')).selectpicker();
})

createComponent({
  name: 'g-select',
  template: /* HTML */`
<style>
  @import url('https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css');
  @import url('https://cdn.jsdelivr.net/npm/bootstrap-select@1.13.14/dist/css/bootstrap-select.min.css');
  /* selectpicker styles */
g-select {
  display: inline-block;
}
g-select span.text:before {
  content: '';
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background-color: #E6E6E6;
  position: absolute;
  left: 17px;
  top:8px;
}

g-select .bs-ok-default:after {
  border-style:none !important;
}

g-select .show-tick .dropdown-menu .selected span.check-mark {
  background-color: #25B8FF;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  left: 17px;
  z-index: 10;
  top: 8px !important;
}
g-select .dropdown-item.active, g-select .dropdown-item:active{
  background-color:transparent !important;
}
/* It is generated dynamically, we are not allowing add default-classes in html. */
g-select .dropdown-menu{
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
g-select .bs-actionsbox, .bs-donebutton, .bs-searchbox{
  padding:0px;
}
/* select title header */
g-select .popover-header{
  text-align:center;
  font-size:14px;
  font-weight:600;
  border-bottom:1px solid rgba(151, 151, 151, 0.27);
  margin-bottom:8px;
}
g-select .popover-header button,
g-select ul .apply-button-group{
  display:none;
}
g-select .dropdown-menu.inner{
  max-height:150px;
}
</style>
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
`,
options: fields['g-select']
})