title: Gramex runs processes

`ProcessHandler` runs processes and streams their output/errors. For example, to see the results of pinging www.google.com, add this to `gramex.yaml`:

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
