// If lodash, g1, jquery are not included, include them

$('[id^="gramexform-"]').each(function () {
  var $this = $(this)
  var url = document.currentScript.src.replace(/js\/embed.js$/, $this.attr('id').replace(/^gramexform-/, 'publish?id='))
  $.getJSON(url)
    .done(function (data) {
      $('.popover-element').template({ fields: JSON.parse(data[0].config).fields})
      // $this.formbuilder(config)
    })
})
