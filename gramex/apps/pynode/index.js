/* eslint-env es6, node */
/* eslint-disable no-console */
// A Python Node.js bridge

const package = require('./package.json')
const path = require('path')
const { spawn } = require('child_process')
const minimist = require('minimist')
const which = require('which')
const WebSocket = require('ws')

const context = {}
// The env variable NODE_PATH must have a SINGLE node_modules path.
// It's parent directory is where yarn is run.
// Defaults to this file's node_modules.
const node_path = process.env.NODE_PATH || path.resolve(__dirname, 'node_modules')

// Report the Error object to the websocket in a standard way
function send_error(error, ws) {
  ws.send(JSON.stringify({
    error: {
      'name': error.name,
      'message': error.message,
      'stack': error.stack
    },
    result: null
  }))
}

// Return a function that sends the passed result to the websocket as JSON.
// If not parseable as JSON, send an error message to the websocket.
function callback(ws) {
  return function (result) {
    try {
      ws.send(JSON.stringify({ error: null, result: result }))
    } catch (e) {
      send_error(e, ws)
    }
  }
}

// Create a Function(*args, code) and call it as function(*values).
// Send the return value as JSON to the websocket. Report any error
function execute(ws, code, args, values) {
  args.push('exports', 'require', 'module', 'process', 'callback', code)
  values.push(exports, require, module, process, callback(ws))
  try {
    const fn = Function.apply(this, args)
    // Within the code, "this" refers to the context global
    const result = fn.apply(context, values)
    if (typeof result != 'undefined')
      ws.send(JSON.stringify({ error: null, result: result }))
  } catch (e) {
    send_error(e, ws)
  }
}


function main() {
  const args = minimist(process.argv.slice(2))
  const port = args.port || 9800
  const wss = new WebSocket.Server({
    port: port,
    // only allow connections from local host
    verifyClient: function (info) {
      const ip = info.req.connection.remoteAddress
      return ip == '::1' || ip == '127.0.0.1'
    }
  })

  // Print a message indicating versions
  console.log('node.js: ' + process.version + ' pynode: ' + package.version +
    ' port: ' + port + ' pid: ' + process.pid + ' NODE_PATH: ' + node_path)

  // Set up the websocket server
  wss.on('connection', function connection(ws) {
    ws.on('message', function incoming(message) {
      'use strict'
      let exec
      try {
        exec = JSON.parse(message)
      } catch (e) {
        send_error(e, ws)
      }
      // Execute code as provided
      if (exec.code) {
        const code = exec.code
        delete exec.code
        let lib = exec.lib
        delete exec.lib
        const args = Object.keys(exec)
        const values = Object.values(exec)

        // Install libraries
        if (!lib)
          lib = []
        else if (!Array.isArray(lib))
          lib = [lib]
        const add = ['add', '--prefer-offline']
        lib.forEach(function (library) {
          try {
            require(library)
          } catch (e) {
            add.push(library)
            console.log('TODO: lib', JSON.stringify(library))
          }
        })
        if (add.length > 2) {
          try {
            console.log('yarn ' + add.join(' '), 'CWD:', path.resolve(node_path, '..'))
            // Run yarn add in the NODE_PATH directory. Defaults to this script's directory
            spawn(which.sync('yarn'), add, { cwd: path.resolve(node_path, '..') })
              .on('close', function () { execute(ws, code, args, values) })
            // TODO: if yarn fails (e.g. invalid module, no network), report error on console
          } catch (e) {
            send_error(e, ws)
          }
        }
        else
          execute(ws, code, args, values)
      } else if (exec.path) {
        ws.send(JSON.stringify({
          error: 'path= is not yet supported',
          result: null
        }))
      } else {
        ws.send(JSON.stringify({
          error: 'Neither code= nor path= was specified',
          result: null
        }))
      }
    })
  })
}

main()
