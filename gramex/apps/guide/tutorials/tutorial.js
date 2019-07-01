// Convert <a class="source">... into a view source and view output button
$('a.source').each(function () {
  var $wrapper = $('<div>').addClass('mx-n3 mt-n3 mb-3 px-3 py-2 d-flex')
  $wrapper.insertBefore(this)
  $wrapper.append(_buttonize($(this), 'See output', this.href, 'btn btn-primary btn-sm mr-2'))
  $wrapper.append(_buttonize($(this).clone(), 'View source', this.href + '.source', 'btn btn-warning btn-sm'))
})

function _buttonize($this, text, href, cls) {
  $this.attr('class', cls)
    .text(text)
    .attr('href', href)
    .attr('target', '_blank')
    .attr('rel', 'noopener')
  return $this
}
