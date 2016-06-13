title: Debugging Gramex

This page documents ways of debugging a Gramex application.

## Debug mode

Run Gramex with a `--settings.debug` to trigger [debug mode][debug-mode] in
Tornado. This auto-reloads templates, Python scripts, etc. when any of them
change.

Press `Ctrl+D` on the console to start the [Python debugger](#python-debugger)
inside Gramex at any time.

[debug-mode]: http://www.tornadoweb.org/en/stable/guide/running.html?highlight=debug#debug-mode-and-automatic-reloading


## Python debugger

The Python debugger lets you stop, inspect and step through code line-by-line.
You can learn more from this
[video tutorial on pdb](https://www.youtube.com/watch?v=lnlZGhnULn4).

There are many ways to start the debugger:

1. Add this line: `import ipdb; ipdb.set_trace()` to your code. Python will
   run until this line and start the debugger.
1. When Gramex is running, you press `Ctrl+D` on the console at any time. Python
   will start the debugger.
1. Run `gramex --settings.debug`. When there's an exception, Python will start
   the debugger at the line before the error. (This was called `debug_exception`
   in Gramex 1.0.7 and `debug.exception` in Gramex 1.0.8. It is not merged into
   `settings.debug`.)
1. Run Gramex via `python -m pdb /path/to/gramex/__main__.py`.

You can use [WinPDB](http://winpdb.org/docs/) -- a cross-platform GUI for
pdb -- on Gramex using:

    :::shell
    conda install -c jacob-barhak -c anaconda winpdb
    winpdb.bat /path/to/gramex/__main__.py

(On Linux / Mac, use `winpdb` instead of `winpdb.bat`.)

Here are some useful things you can do on the debugger:

- Break at a function: `b <function>`, then run by typing `c`.
- Reload a module. `import(<module>); reload(<module>)`
- Print Gramex URL configuration. `import gramex, yaml; p yaml.dump(gramex.conf.url)`

Useful commands you can use on the debugger:

    c                 # Continue running the program
    pp value          # Pretty-print value
    !<python-code>    # Run the Python code in the current context
    b function        # Set a breakpoint at a function
    b file:line       # Set a breakpoint at file, on line
    clear function    # Clear breakpoint at a function
    s or step         # Step into the current line's function
    n or next         # Next line (without entering the current function)
    l or list         # List the code
    h or help         # Help -- list available commands


## Print statements

You can add print statements to your code to show whether a line is reached, and
what a variable's value is.

A few suggestions:

1. Always print the variable name, e.g. `print("var", var)` instead of just
   `print(var)`. This makes it easier to understand what is being printed
2. Use `pprint.pprint` to print complex variables
3. Prefix multi-line prints with 2 newline. For example,
   `print('\n\n'); print("longvar", longvar)`
4. Remove all print statements before committing your code into the `master` or
   `dev` branch.


## Reloading

Gramex can [autoreload](http://www.tornadoweb.org/en/stable/autoreload.html) if
any dependent Python files change. To enable this behaviour, use the following
settings in `gramex.yaml`:

    :::yaml
    app:
        settings:
            debug: true

Or use it from the command line:

    :::shell
    gramex --settings.debug=true

**This uses a lot of CPU**. It also serves tracebacks on error. Do not enable
this on production systems.

## Profiling

`gramex.debug` provides support for timing and line profiling via `timer`,
`Timer` and `lineprofile`.

### Timer

`timer()` prints the time since last called. For example:

    :::python
    from gramex.debug import timer

    def function(handler):
        timer('start')
        some_code()
        timer('ran some_code()')

prints this log message:

    I 05-May 08:16:38 debug:54 0.102s start [module.function:56]
    I 05-May 08:16:38 debug:54 0.012s ran some_code() [module.function:58]

The log message includes the time taken to get to the line (e.g. `0.102s`), the
message logged, and the `module.function:line-number` from where the `timer()`
was called.


`Timer()` is similar to `timer()`, but shows the time for an block of code. For
example:

    :::python
    from gramex.debug import Timer

    def function(handler):
        with Timer('run some_code()'):
            some_code()

prints this log message:

    I 05-May 08:16:38 debug:54 0.012s run some_code() [module.function:56]

The log message includes the time taken to get to the line (e.g. `0.102s`), the
message logged, and the `module.function:line-number` from where the `Timer()`
was called.


`lineprofile` is a decorator that prints the time taken for each line of a
function every time it is called. For example:

    :::python
    from gramex.debug import lineprofile

    @lineprofile
    def function(handler):
        # ... your code here...

prints line-by-line statistics about the function. This requires the
[line_profiler](https://github.com/rkern/line_profiler) module to run.
