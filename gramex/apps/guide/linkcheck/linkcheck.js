// Recursively spider a local URL to see if all responses succeed
var _linkcheck_cache = {}

$.fn.linkcheck = function(url, depth, base_url) {
  if (depth <= 0)
    return
  url = $('<a></a>').attr('href', url).get(0).href
  var $link = $('<a></a>').attr('href', url).text(url.replace(base_url, ''))
  var $item = $('<li></li>').append($link).appendTo(this)

  _linkcheck_cache[url] = true
  $.ajax(url, { dataType: 'text' })
    .done(function(data, statusText, xhr) {
      $link.addClass('ok')
      var mime = xhr.getResponseHeader('Content-Type')
      if (!mime.match(/^text\/html/i))
        return

      // Parse links relative to url
      var doc = document.implementation.createHTMLDocument('')
      doc.documentElement.innerHTML = data
      doc.head.appendChild(doc.createElement('base')).href = url

      // Add all anchor and image links
      var links = []
      $('a', doc).each(function() { links.push(this.href.replace(this.hash, '')) })
      $('img', doc).each(function () { links.push(this.src.replace(this.hash, '')) })
      links.forEach(function(link) {
        if (!(link in _linkcheck_cache) && (link.slice(0, url.length) == url))
          $('<ul></ul>').appendTo($item).linkcheck(link, depth - 1, url)
      })
    })
    .fail(function(xhr) {
      $link.addClass('fail')
        .append(' <span>' + xhr.status + ': ' + xhr.statusText + '</span>')
    })
}
