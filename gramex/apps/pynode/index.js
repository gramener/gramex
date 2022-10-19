/* eslint-env es6, node */
/* eslint-disable no-console */
// A Python Node.js bridge

const package = require("./package.json");
const child_process = require("child_process");
const minimist = require("minimist");
const which = require("which");
const WebSocket = require("ws");

const context = {};
const cwd = process.cwd();

// Report the Error object to the websocket in a standard way
function send_error(error, ws) {
  ws.send(
    JSON.stringify({
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      result: null,
    })
  );
}

// Return a function that sends the passed result to the websocket as JSON.
// If not parseable as JSON, send an error message to the websocket.
function callback(ws) {
  return (result) => {
    try {
      ws.send(JSON.stringify({ error: null, result: result }));
    } catch (e) {
      send_error(e, ws);
    }
  };
}

// Create a Function(*args, code) and call it as function(*values).
// Send the return value as JSON to the websocket. Report any error
function execute(ws, code, args, values) {
  args.push("exports", "require", "module", "process", "callback", code);
  values.push(exports, require, module, process, callback(ws));
  try {
    const fn = Function.apply(this, args);
    // Within the code, "this" refers to the context global
    const result = fn.apply(context, values);
    // If the code didn't return anything, return null
    ws.send(
      JSON.stringify({
        error: null,
        result: typeof result == "undefined" ? null : result,
      })
    );
  } catch (e) {
    send_error(e, ws);
  }
}

function main() {
  const args = minimist(process.argv.slice(2));
  const port = args.port || 9800;
  const wss = new WebSocket.Server({
    port: port,
    // Only allow connections from local host.
    // Localhost can be ::::ffff:127.0.0.1 (IPv6) or 127.0.0.1 (IPv4) or '::1'
    verifyClient: (info) =>
      info.req.connection.remoteAddress.match(/\b127.0.0.1$|^::1$/),
  });

  // Print a message indicating versions. pynode.py EXPLICITLY checks for this message.
  console.log(
    `node.js: ${process.version} pynode: ${package.version} port: ${port} pid: ${process.pid} cwd: ${cwd}`
  );

  // Set up the websocket server
  wss.on("connection", (ws) => {
    ws.on("message", (message) => {
      "use strict";
      let exec;
      try {
        exec = JSON.parse(message);
      } catch (e) {
        return send_error(e, ws);
      }
      // Execute code as provided
      if (exec.code) {
        const code = exec.code;
        delete exec.code;
        let lib = exec.lib;
        delete exec.lib;
        const args = Object.keys(exec);
        const values = Object.values(exec);

        // Install libraries
        if (!lib) lib = [];
        else if (!Array.isArray(lib)) lib = [lib];
        const add = ["install"];
        lib.forEach((library) => {
          try {
            require(library);
          } catch (e) {
            add.push(library);
          }
        });
        // add = [install, lib1, lib2, ...]. If there's something more than 'install', install it
        if (add.length > 1) {
          // NOTE: In Windows, installing a library requires a restart
          try {
            console.log(`npm ${add.join(" ")} at ${cwd}`);
            let npm = child_process
              .spawn(which.sync("npm"), add, { cwd: cwd })
              .on("error", console.error)
              .on("close", () => execute(ws, code, args, values));
            npm.stdout.on("data", (data) => console.log(data.toString()));
            npm.stderr.on("data", (data) => console.log(data.toString()));
          } catch (e) {
            send_error(e, ws);
          }
        } else execute(ws, code, args, values);
      } else if (exec.path)
        send_error(
          {
            name: "Unsupported argument",
            message: "path= is not yet supported",
          },
          ws
        );
      else
        send_error(
          { name: "Missing arguments", message: "Need code= or path=" },
          ws
        );
    });
  });
}

main();
