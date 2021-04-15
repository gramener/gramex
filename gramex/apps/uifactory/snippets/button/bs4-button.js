/* globals uifactory, fields */

uifactory.register({
  name: 'bs4-button',
  template: /* HTML */`
<style>
  @import url('https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/css/bootstrap.min.css');
  .aspect-ratio-1 {
    aspect-ratio: 1;
    width: var(--size, 60px);
    height: var(--size, 60px);
  }
</style>
<% var klass = {} %>
<!-- size: ['', 'small', 'large'] -->
<% klass.sizeClass = size === 'small' ? 'btn-sm' : size === 'large' ? 'btn-lg' : '' %>
<!-- color: ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'white'] -->
<!-- outline: [true, false] -->
<% klass.styleClass = outline === 'true' ? 'btn-outline-' + color : 'btn-' + color %>

<!-- gradient: [true, false] -->
<% klass.gradientClass = gradient === 'true' ? 'bg-gradient' : '' %>

<!-- transparent: [true, false] -->
<% klass.transparentClass = transparent === 'true' ? 'bg-transparent' : '' %>

<!-- link: [true, false] -->
<% klass.linkClass = link === 'true' ? 'btn-link' : '' %>

<!-- shape: ['', 'pill', 'circle'] -->
<% klass.shapeClass = shape === 'pill' ? 'rounded-pill' : shape === 'circle' ? 'rounded-pill aspect-ratio-1 d-flex align-items-center justify-content-center' : '' %>

<!-- border: [true, false] -->
<% klass.borderClass = border === 'true' ? 'border' : '' %>
<!-- borderSize: [1, 2, 3, 4, 5] -->
<% klass.borderSize = border === 'true' && borderSize ? borderSize : 0 %>
<!-- borderSize: [1, 2, 3, 4, 5] -->
<% klass.borderSizeClass = border === 'true' && borderSize ? 'border-' + borderSize : '' %>
<!-- border-Color: ['primary','secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'white'] -->
<% klass.borderColorClass = border === 'true' && borderColor ? 'border-' + borderColor : '' %>
<!-- borderRounded: [true, false] -->
<% klass.borderRoundedClass = borderRounded === 'true' ? 'rounded' : '' %>
<!-- borderRadiusPosition: ['top', 'end', 'bottom', 'start'] -->
<% klass.borderRadiusPositionClass = borderRounded === 'true' && borderRadiusPosition ? 'rounded-' + borderRadiusPosition : '' %>

<% var iconClass = {} %>
<% iconClass.library = obj['iconLibrary'] ? obj['iconLibrary'] : 'bi' %>
<% iconClass.type = obj['iconType'] ? iconClass.library + '-' + obj['iconType'] : 'd-none' %>
<!-- iconPosition: ['start', 'end'] -->
<% iconClass.position = obj['iconPosition'] ? 'float-' + obj['iconPosition']  : '' %>

<button type="<%= type %>" class="btn <%= Object.values(klass).join(' ') %>">
  <i class="<%- Object.values(iconClass).join(' ') %>"></i>
  <%= label %>
</button>`,
properties: fields['bs4-button']
})
