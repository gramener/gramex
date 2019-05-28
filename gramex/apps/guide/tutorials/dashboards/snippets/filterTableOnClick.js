  function filterTableOnClick(event, item) {
    var qparts = {};
    Object.entries(item.tooltip || item.datum).forEach(([key, val]) => {
      if (!(key == "Sales")) {
        qparts[key] = val;
      }
    })
    if (_.isEmpty(qparts)) { return }
    var url = g1.url.parse(location.hash.replace('#', ''))
    location.hash = url.update(qparts).toString();
  }
