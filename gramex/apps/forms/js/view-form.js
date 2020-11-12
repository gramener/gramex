/* globals form_id */

const resolutions = {
  laptop: {
    resX: 1080,
    resY: 1920,
    devicePixelRatio: 3
  },
  tablet: {
    resX: 640,
    resY: 980,
    devicePixelRatio: 2
  },
  mobile: {
    resX: 640,
    resY: 980,
    devicePixelRatio: 2
  }
}

$(function() {
  $('.btn.viewsource').addClass('d-none')
  $.ajax(`../embed/${form_id}.html`, {
    success: function(data) {
      $('#view-form').html(data)
      $('pre code.language-html').html(escapeHtml($('#view-form').html()))
      document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block)
      })
    }
  })
})

// escape html tags to show source code
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

$('body').on('click', 'button#toggle-source', function() {
  if($('.btn.viewsource').hasClass('d-none')) {
    $('.btn.viewsource').removeClass('d-none')
    $('.sourcecode-container').removeClass('d-none')
  } else {
    $('.btn.viewsource').addClass('d-none')
    $('.sourcecode-container').addClass('d-none')
  }
}).on('click', 'button[data-device]', function() {
  const device = $(this).data('device')
  const width = resolutions[device].resX/resolutions[device].devicePixelRatio
  const height = resolutions[device].resY/resolutions[device].devicePixelRatio

  $('#preview').removeClass('d-none')

  document.getElementById('preview').style.width = width + "px"
  document.getElementById('preview-body').style.height = height + "px"
  document.getElementById('frame').srcdoc = document.getElementById('view-form').innerHTML

  document.getElementById('frame').width = width
  document.getElementById('frame').height = height

  // setTimeout since content needs to load before style is applied
  setTimeout(function() {
    let $head = $("#frame").contents().find("head")
    $head.append($("<link/>"), {
      rel: "stylesheet",
      href: "https://fonts.googleapis.com/css2?family=Comfortaa&display=swap"
    })
    $head.append($("<link/>", {
      rel: "stylesheet",
      href: "../style.css",
      type: "text/css"
    }))
    // TODO: font doesn't get applied to iframe content yet
    document.getElementById("frame").contentDocument.body.style.fontFamily = "Comfortaa"
  }, 100) // setTimeout
}) // click event
