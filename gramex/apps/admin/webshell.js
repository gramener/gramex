/* eslint-env browser, jquery */
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
  var history = {states: [], index: -1, current: ''}
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

    function write(msg, html) {
      $('<div>')[html ? 'html' : 'text'](msg).appendTo($terminal)
      $terminal.scrollTop(terminal.scrollHeight)
    }

    var ws
    function connect() {
      ws = new WebSocket(ws_url)
      opt.welcome.forEach(write)
      // On command response, clear the prompt, write to terminal
      ws.onmessage = function (msg) {
        $prompt.val('').focus()
        write(msg.data)
      }
    }
    $terminal.on('click', '.reload', connect)
    connect()

    // When user submits a command, send it to the websocket, or write a helpful error.
    $('form', this).on('submit', function (e) {
      e.preventDefault()
      if (ws.readyState != 1) {
        write('Connection closed. <span class="reload btn btn-primary">Reconnect</span> or press F12 and check the JavaScript error log.', true)
        return
      }
      var cmd = $prompt.val()
      try {
        ws.send(cmd)
      } catch (e) {
        write(e)
      }
      write(opt.prompt + cmd)
      if (history.states[history.states.length - 1] != cmd)
        history.states.push(cmd)
      history.index = -1
      history.current = ''
      $prompt.val('')
    })

    $('form', this).on('keydown', function (e) {
      var index = history.index,
          last = history.states.length - 1
      if (e.key == 'ArrowUp') {
        e.preventDefault()                // Don't move cursor to start of text
        if (index < last) index++         // Go up to the earliest history index
      } else if (e.key == 'ArrowDown') {
        if (index >= 0) index--           // Go up to -1 (indicates blank line)
      } else if (history.index == -1) {   // For other chars, if last entry is changed
        history.current = $prompt.val()   // store it
      }
      if (history.index != index) {
        $prompt.val(history.states[last - index] || history.current)
        history.index = index
      }
    })

    if (opt.focus)
      $prompt.focus()
  })
}
