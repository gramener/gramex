uifactory.register({
  name: 'g-button',
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
<% klass.borderSizeClass = border === 'true' && border-size ? 'border-' + border-size : '' %>
<!-- border-Color: ['primary','secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'white'] -->
<% klass.borderColorClass = obj['border-color'] ? 'border-' + obj['border-color'] : '' %>
<!-- borderRounded: [true, false] -->
<% klass.borderRoundedClass = obj['border-rounded'] === 'true' ? 'rounded' : '' %>
<!-- borderRadiusSize: [0, 1, 2, 3] -->
<% klass.borderRadiusSizeClass = obj['border-rounded'] === 'true' && obj['border-radius-size'] ? 'rounded-' + obj['border-radius-size'] : '' %>
<!-- borderRadiusPosition: ['top', 'end', 'bottom', 'start'] -->
<% klass.borderRadiusPositionClass = obj['border-radius-position'] ? 'rounded-' + obj['border-radius-position'] : '' %>

<% var iconClass = {} %>
<% iconClass.library = obj['icon-library'] ? obj['icon-library'] : 'bi' %>
<% iconClass.type = obj['icon-type'] ? iconClass.library + '-' + obj['icon-type'] : 'd-none' %>
<!-- iconPosition: ['start', 'end'] -->
<% iconClass.position = obj['icon-position'] ? 'float-' + obj['icon-position']  : '' %>

<button type="<%= type %>" class="btn <%= Object.values(klass).join(' ') %>">
  <i class="<%- Object.values(iconClass).join(' ') %>"></i>
  <%= label %>
</button>`,
options: fields['g-button']
})
