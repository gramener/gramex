---
title: ProcessHandler runs programs
prefix: ProcessHandler
...

[TOC]

[ProcessHandler][processhandler] runs processes and streams their output/errors. For example, to
see the results of an `nslookup www.google.com`, add this to `gramex.yaml`:

    :::yaml
    url:
        nslookup-google:
            pattern: /nslookup-google             # At this URL
            handler: ProcessHandler               # run a process
            kwargs:
                args: nslookup www.google.com     # The full command to run
                shell: true                       # using the shell
                buffer: line                      # Show the result line by line
                headers:
                    Content-Type: text/x-plain    # as a text file

See the results of this at [nslookup-google](nslookup-google).

`args` is a list of command line arguments. If you use `shell: true`, you can
specify `args` as a single command that will be run on the shell.

`buffer` indicates the size of the buffer. This can be a number of bytes to
buffer before flushing, or `line` to flush the output after every line.

(Note: we use the Content-Type `text/x-plain` instead of `text-plain` because
`text/plain` is buffered by the browser, and you will cannot see the live
updates.)

After the handler executes, users can be redirected via the `redirect:` config
documented the [redirection configuration](../config/#redirection).


## ProcessHandler redirection

You can redirect `stdout` and `stderr` from the process. For example, this URL
[nslookup-google-file](nslookup-google-file) saves `stdout` to
[nslookup.txt](nslookup.txt) as well as displays the output. It hides the
`stderr`:

    :::yaml
    url:
        nslookup-google-file:
            pattern: /nslookup-google-file
            handler: ProcessHandler
            kwargs:
                args: nslookup -n 4 www.google.com
                shell: true
                buffer: line
                stdout:
                    - $YAMLPATH/nslookup.txt    # Redirect to nslookup.txt in same folder as YAML file
                    - pipe                  # Additionally, display the output
                stderr: false               # Hide the stderr output
                headers:
                    Content-Type: text/x-plain

[processhandler]: https://learn.gramener.com/gramex/gramex.handlers.html#gramex.handlers.ProcessHandler
