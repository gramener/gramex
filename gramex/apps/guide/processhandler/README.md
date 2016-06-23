title: Gramex runs processes

`ProcessHandler` runs processes and streams their output/errors. For example, to
see the results of pinging www.google.com, add this to `gramex.yaml`:

    :::yaml
    url:
        ping-google:
            pattern: /ping-google                 # At this URL
            handler: ProcessHandler               # run a process
            kwargs:
                args: ping -n 4 www.google.com    # The full command to run
                shell: true                       # using the shell
                buffer: line                      # Show the result line by line
                headers:
                    Content-Type: text/x-plain    # as a text file

See the results of this at [ping-google](ping-google).

`args` is a list of command line arguments. If you use `shell: true`, you can
specify `args` as a single command that will be run on the shell.

`buffer` indicates the size of the buffer. This can be a number of bytes to
buffer before flushing, or `line` to flush the output after every line.

(Note: we use the Content-Type `text/x-plain` instead of `text-plain` because
`text/plain` is buffered by the browser, and you will cannot see the live
updates.)

## ProcessHandler redirection

You can redirect `stdout` and `stderr` from the process. For example, this URL
[ping-google-file](ping-google-file) saves `stdout` to [ping.txt](ping.txt) as
well as displays the output. It hides the `stderr`:

    :::yaml
    url:
        ping-google-file:
            pattern: /ping-google-file
            handler: ProcessHandler
            kwargs:
                args: ping -n 4 www.google.com
                shell: true
                buffer: line
                stdout:
                    - $YAMLPATH/ping.txt    # Redirect to ping.txt in same folder as YAML file
                    - pipe                  # Additionally, display the output
                stderr: false               # Hide the stderr output
                headers:
                    Content-Type: text/x-plain
