/* globals g1 */

$(function () {
  try {
    var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
    var synth = window.speechSynthesis
    main(recognition, synth)
  }
  catch (err) {
    $('.no-speech-api').removeClass('d-none')
  }
})

function main(recognition, synth) {
  var listening = false
  recognition.lang = 'en-US'
  recognition.continuous = true

  $.getJSON('suggestion')
    .done(function (data) {
      data.forEach(function (d) {
        $('.sample-questions').append('<li class="list-group-item">' + d + '</li>')
      })
    })

  function start_listening() {
    if (listening)
      return
    listening = true
    $('.mic').addClass('btn-danger').removeClass('btn-primary')
    $('.speak-btn-text').text('Listening...')
    recognition.start()
  }
  function stop_listening() {
    if (!listening)
      return
    listening = false
    $('.mic').addClass('btn-primary').removeClass('btn-danger')
    $('.speak-btn-text').text('Ask me')
    recognition.stop()
  }
  $('.mic').on('click', function () {
    if (listening) stop_listening()
    else start_listening()
  })
  recognition.onspeechend = stop_listening

  recognition.onresult = function (event) {
    stop_listening()

    var text = event.results[event.results.length - 1][0].transcript
    $('.user-question').text(text)
    $('.you-said').show()
    $('.speak-btn-text').text('Searching...')

    $.getJSON('get_answer', { q: text })
      .done(function (result) {
        $('.speak-btn-text').text('Ask me')
        $('.result').removeClass('d-none')
        $('.user-question').html(text)
        $('.you-said, .my-answer').show()
        $('.did-you-mean').hide()
        $('.guess-question').html(result.question)
        $('.default-answer').html(result.answer)
        if (result.similarity < 0.5)
          $('.default-answer').html('I did not understand')
        else if (result.similarity < 0.75)
          $('.did-you-mean').show()
        if (synth)
          synth.speak(new SpeechSynthesisUtterance($('.default-answer').html()))
      })
  }

  // If the URL has a ?refreshed, show the alert message for 2 seconds and close it
  var url = g1.url.parse(location.href)
  if ('refreshed' in url.searchKey) {
    $('.refresh-success').removeClass('d-none')
    setTimeout(function () {
      $('.refresh-success').alert('close')
    }, 2000)
  }
}
