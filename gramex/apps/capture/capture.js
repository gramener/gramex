/* globals phantom */
/* eslint-disable no-console, no-unused-vars */

var version = '1.0.0'
var server_version = 'Capture/' + version

// If you want to specify a header or footer, return an object with two keys:
// height and contents. A typical height setting is '2.54cm' -- one inch.
// `contents` must be a phantom.callback() wrapped function that accepts 2
// parameters (page number and total page count) and returns a string. The
// string is displayed as HTML.
function header(args) {
  return {
    height: '1cm',
    contents: phantom.callback(function(pageNum, numPages) { return '' })
  }
}
function footer(args) {
  var title = args.title || ''
  var date = new Date()
  return {
    height: '1cm',
    contents: phantom.callback(function(pageNum, numPages) {
      return (
        '<div>' +
          '<div style="position:absolute;left:3em;">' + title + '</div>' +
          '<div style="position:absolute;width:100%;text-align:center">' + date + '</div>' +
          '<div style="position:absolute;right:3em">Page ' + pageNum + ' of ' + numPages + '</div>' +
        '</div>'
      )
    })
  }
}
function margin(args) {
  return {
    'top': '1cm',
    'right': '1cm',
    'bottom': '1cm',
    'left': '1cm'
  }
}


var fs = require('fs')
var system = require('system')
var server = require('webserver').create()
var phantom_version = phantom.version.major + '.' + phantom.version.minor + '.' + phantom.version.patch
var error

// This app requires a minimum version of PhantomJS
if (phantom_version < '2.1.1') {
  console.error('Requires PhantomJS 2.1.1 or above, not', phantom_version)
  phantom.exit(1)
}

// Render a URL based on parameters provided in q.
// Save the result in a file, and call callback(file).
function render(q, callback) {
  error = {status: '', msg: []}
  q.ext = q.ext || 'pdf'
  q.file = (q.file || 'screenshot') + '.' + q.ext
  if (fs.exists(q.file))
    fs.remove(q.file)

  var page = require('webpage').create()
  if (q.ext.match(/^pdf$/i)) {
    page.paperSize = {
      format: (q.format || 'A4'),
      orientation: decodeURIComponent(q.orientation || 'portrait'),
      margin: margin(q),
      header: header(q),
      footer: footer(q)
    }
  } else {
    var scale = parseFloat(q.scale || '1'),
        width = parseFloat(q.width || '1200'),
        height = 768
    if (q.height) {
      height = parseFloat(q.height || '768')
      page.clipRect = {
        top: 0,
        left: 0,
        width: width,
        height: height
      }
    }
    page.zoomFactor = scale
    page.viewportSize = {width: width, height: height}
  }

  page.clearCookies()
  if (q.cookie) {
    var url = parseUri(q.url)
    var cookies = parseCookie(q.cookie)
    for (var name in cookies) {
      page.addCookie({name: name, value: cookies[name], domain: url.host, path: url.path})
    }
  }

  function save() {
    console.log('Saving', q.url, 'to', q.file)
    page.render(q.file)
    callback(q.file)
  }

  // In case PhantomJS is unable to load the page, log the error
  page.onResourceError = function(r) {
    error.msg.push(r)
    console.error('ERR:', r.errorCode, r.url, r.errorString)
  }

  var debug = +q.debug
  if (debug >= 2)
    page.onResourceRequested = function(r) { console.log('REQ:', r.url) }
  if (debug >= 1) {
    page.onResourceReceived = function(r) { console.log('GOT:', r.status, r.statusText, r.url) }
    page.onConsoleMessage = function(msg) { console.log('console.log:' + msg) }
  }

  // Open the page
  console.log('Opening', q.url)
  page.open(q.url, function(status) {
    setTimeout(function() {
      error.status = status
      if (status == 'fail')
        return callback()
      // If a selector is specified (for images), set the clipRect.
      if (q.selector) {
        var clipRect = page.evaluate(function(selector) {
          var query = document.querySelector(selector)
          if (query)
            return query.getBoundingClientRect()
        }, decodeURIComponent(q.selector))
        if (clipRect) {
          page.clipRect = {
            top: clipRect.top,
            left: clipRect.left,
            width: clipRect.width,
            height: clipRect.height
          }
        }
      }
      if (q.js) {
        var js = decodeURIComponent(q.js)
        if (q.js.match(/^http/))
          page.includeJs(js, save)
        else {
          fs.write('inject.js', js, 'w')
          if (!page.injectJs('inject.js'))
            console.log('Failed to inject JS')
          save()
          fs.remove('inject.js')
        }
      }
      else
        save()
    }, parseFloat(q.delay || 0))
  })
}


var homepage = (function(script) {
  var parts = script.split(/[/\\]/)
  parts[parts.length - 1] = 'index.html'
  return parts.join('/')
})(system.args[0])

function webapp(request, response) {
  // http://phantomjs.org/api/webserver/method/listen.html is wrong.
  // PhantomJS 1.9.7 on Windows has a request.postRaw string and request.post object
  // PhantomJS 1.9.8 on Linux has a request.post string and no request.postRaw
  // PhantomJS 2.0.1 onwards encodes URIs. https://github.com/ariya/phantomjs/pull/12233
  // We handle all scenarios here
  /* eslint-disable indent */
  var q = parseUri(
    request.postRaw ? '/?' + request.postRaw :
    request.post    ? '/?' + request.post :
    phantom_version >= '2.0.1' ? decodeURIComponent(request.url) : request.url
  ).queryKey
  /* eslint-enable indent */
  if (!q.url) {
    response.statusCode = 200
    response.headers = {
      'Content-Type': 'text/html',
      'Server': server_version
    }
    response.write(fs.read(homepage))
    return response.close()
  }

  q.url = decodeURIComponent(q.url)
  q.delay = decodeURIComponent(q.delay || 0)
  q.cookie = q.cookie ? decodeURIComponent(q.cookie).replace(/\+/g, ' ') : request.headers.Cookie

  render(q, function(file) {
    if (error.status == 'fail') {
      response.statusCode = 500
      response.headers = {
        'Server': server_version,
        'Content-Type': 'application/json'
      }
      response.write(JSON.stringify(error))
      response.close()
    } else {
      response.statusCode = 200
      response.headers = {
        'Server': server_version,
        'Content-Type': mime(file),
        'Content-Disposition': 'attachment; filename=' + file
      }
      response.setEncoding('binary')
      response.write(fs.read(file, 'b'))
      response.close()
      // Remove the file after serving it
      fs.remove(file)
    }
  })
}

function main() {
  var args = {}
  system.args.forEach(function(arg) {
    var match = arg.match(/^--(.*?)=(.*)/i)
    if (match)
      args[match[1]] = match[2]
  })

  // Render the server if a port is specified
  // If no arguments are specified, start the server on a default port
  // Otherwise, treat it as a command line execution
  if (args.port || system.args.length <= 1) {
    var port = parseInt(args.port || 8080)
    var listening = server.listen(port, webapp)
    if (listening) {
      console.log(
        'PhantomJS:', phantom_version,
        'capture.js:', version,
        'port:', port)
    } else {
      console.log('Could not bind to port', port)
      phantom.exit(1)
    }
  } else {
    render(args, function() {
      phantom.exit()
    })
  }
}

main()

function mime(file) {
  /* eslint-disable indent */
  return (
    file.match(/\.pdf$/i) ? 'application/pdf' :
    file.match(/\.png$/i) ? 'image/png' :
    file.match(/\.gif$/i) ? 'image/gif' :
    file.match(/\.jpg$/i) ? 'image/jpeg' :
                            'application/octet-stream')
  /* eslint-enable indent */
}

// parseUri 1.2.2
// (c) Steven Levithan <stevenlevithan.com>
// MIT License

function parseUri(str) {
  var o   = parseUri.options,
      m   = o.parser[o.strictMode ? 'strict' : 'loose'].exec(str),
      uri = {},
      i   = 14

  while (i--) uri[o.key[i]] = m[i] || ''

  uri[o.q.name] = {}
  uri[o.key[12]].replace(o.q.parser, function ($0, $1, $2) {
    if ($1) uri[o.q.name][$1] = $2
  })

  return uri
}

parseUri.options = {
  strictMode: false,
  key: ['source','protocol','authority','userInfo','user','password','host','port','relative','path','directory','file','query','anchor'],
  q: {
    name:   'queryKey',
    parser: /(?:^|&)([^&=]*)=?([^&]*)/g
  },
  parser: {
    // eslint-disable-next-line no-useless-escape
    strict: /^(?:([^:\/?#]+):)?(?:\/\/((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?))?((((?:[^?#\/]*\/)*)([^?#]*))(?:\?([^#]*))?(?:#(.*))?)/,
    // eslint-disable-next-line no-useless-escape
    loose:  /^(?:(?![^:@]+:[^:@\/]*@)([^:\/?#.]+):)?(?:\/\/)?((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?)/
  }
}

// https://www.quirksmode.org/js/cookies.html

function parseCookie(str) {
  for(var result={}, parts=str.split(';'), i=0; i < parts.length; i++) {
    var frags = parts[i].trim().split('=')
    result[frags[0]] = frags.slice(1).join('=')
  }
  return result
}
