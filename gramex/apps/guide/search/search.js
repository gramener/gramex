/* globals lunr */
$('#index').each(function() {
  var $index = $(this)
  var prefix = $index.data('prefix') || ''
  $.ajax($index.data('url'))
    .done(function(data) {
      var terms = []
      for (var page in data)
        for (var frag in data[page])
          if (frag)
            for (var term in data[page][frag])
              terms.push([term, page + (frag ? '#' + frag : '')])
      terms.sort(function(a, b) {
        var x = a[0].toLowerCase(),
            y = b[0].toLowerCase()
        return x < y ? -1 : x > y ? +1 : 0
      })
      terms.forEach(function(row) {
        $index.append('<a href="' + prefix + row[1] + '">' + row[0] + '</a>')
      })
    })
})

$('#search').each(function() {
  var $search = $(this)
  var prefix = $search.data('prefix') || ''
  var $results = $('<div></div>').attr('id', 'searchresults').insertAfter(this)
  $.ajax($search.data('url'))
    .done(function(index) {
      var idx = lunr.Index.load(index.index)
      var docs = index.docs
      $search
        .val(location.hash.replace(/^#/, ''))
        .on('input', function() {
          var text = $(this).val().replace(/^\s+/, '').replace(/\s+$/, '')
          if (text) {
            var results = idx.search(text)
            if (results.length)
              $results.html(results.slice(0, 20).map(function(result) {
                var d = docs[result.ref]
                return '<div><a href="' + prefix + d.link + '">' + d.prefix + ' &raquo; ' + d.title + '</a></div>'
              }))
          } else {
            $results.html('')
          }
        })
        .trigger('input')
    })
})
