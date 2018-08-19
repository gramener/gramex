/* globals $ */
// TODO: detailed docs

$.fn.webshell = function(options) {
  var opt = options || {}
  opt.height = opt.height || '300px'
  opt.terminal_class = opt.terminal_class || 'bg-dark text-light'
  opt.terminal_class += ' terminal m-0 p-2 '
  opt.prompt_class = opt.prompt_class || 'bg-secondary text-light'
  opt.prompt_class += ' prompt w-100 text-monospace m-0 p-2 border-0'
  opt.prompt = opt.prompt || '> '
  opt.focus = opt.focus || false
  opt.welcome = opt.welcome || []
  if (!Array.isArray(opt.welcome))
    opt.welcome = [opt.welcome]
  opt.url = opt.url || 'webshell'
  // opt.url can be a relative URL. Make it absolute relative to the page.
  // Ensure that we use ws:// or wss:// based on the current location
  var ws_url = $('<a>').attr('href', opt.url).get(0).href.replace(/^http/, 'ws')

  this.addClass('d-flex flex-column')
  this.each(function() {
    // Insert the terminal
    this.style.height = opt.height
    var $terminal = $('<pre>').addClass(opt.terminal_class).appendTo(this)
    var terminal = $terminal.get(0)
    // Add forced styling
    terminal.style.whiteSpace = 'pre-wrap'
    terminal.style.overflowWrap = 'break-word'
    terminal.style.overflowY = 'auto'
    // Insert the prompt
    $(this).append('<form><input></form>')
    var $prompt = $('input', this).addClass(opt.prompt_class)

    function write(msg) {
      $('<div>').text(msg).appendTo($terminal)
      $terminal.scrollTop(terminal.scrollHeight)
    }

    opt.welcome.forEach(write)

    var ws = new WebSocket(ws_url)
    // On command response, clear the prompt, write to terminal
    ws.onmessage = function (msg) {
      $prompt.val('').focus()
      write(msg.data)
    }
    // When clicking on the terminal, focus on the input
    $terminal.on('click', function() {
      $prompt.focus()
    })
    // When user submits a command, send it to the websocket, or write a helpful error.
    $('form', this).on('submit', function (e) {
      e.preventDefault()
      if (ws.readyState != 1) {
        write('Websocket closed. Try reloading. Or press F12 and check the JavaScript error log.')
        return
      }
      cmd = $prompt.val()
      try {
        ws.send(cmd)
      } catch (e) {
        write(e)
      }
      write(opt.prompt + cmd)
      $prompt.val('')
    })

    if (opt.focus)
      $prompt.focus()
  })
}
