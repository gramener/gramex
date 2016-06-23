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
