$(function() {
  $('body').on('click', '.post-button', function(e) {
    e.preventDefault()
    var target = $(this).data('target')
    $.ajax({
      type: 'POST',
      url: $(this).data('href'),
      contentType: 'application/json;charset=utf-8',
      data: JSON.stringify($(this).data('body')),
      dataType: 'json',
      success: function (data) {
        $(target).text(JSON.stringify(data, null, '  '))
      }
    })
  })
})
