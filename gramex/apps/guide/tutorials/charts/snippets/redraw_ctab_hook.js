  $('body').urlfilter({target: 'pushState'})
  $(window).on('#', redrawChartFromURL)
    .urlchange()
