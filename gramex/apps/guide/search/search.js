/* globals lunr */
$.ajax('search.json')
  .done(function(data) {
    var terms = [],
        $index = $('#index')
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
      $index.append('<a href="../' + row[1] + '">' + row[0] + '</a>')
    })
  })

$.ajax('searchindex.json')
  .done(function(index) {
    var idx = lunr.Index.load(index.index)
    var docs = index.docs
    var $results = $('#searchresults')
    $('#search')
      .val(location.hash.replace(/^#/, ''))
      .on('input', function() {
        var text = $(this).val().replace(/^\s+/, '').replace(/\s+$/, '')
        if (text) {
          var results = idx.search(text)
          if (results.length)
            $results.html(results.slice(0, 20).map(function(result) {
              var d = docs[result.ref]
              return '<div><a href="../' + d.link + '">' + d.prefix + ' &raquo; ' + d.title + '</a></div>'
            }))
        } else {
          $results.html('')
        }
      })
      .trigger('input')
  })
