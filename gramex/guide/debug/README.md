title: Debugging Gramex

This page documents ways of debugging a Gramex application.

## Python debugger

The Python debugger lets you stop and step through code line-by-line. Add this
code anywhere in your function:

    import ipdb; ipdb.set_trace()     # BREAKPOINT

If you don't have IPython, you can also use the Python debugger.

    import pdb; pdb.set_trace()       # BREAKPOINT

When Python runs this line, it stops and opens an debugger. You can run any
Python command from the prompt. For example:

    print(variable)                             # print a variable
    import pprint; pprint.pprint(variable)      # pretty-print a complex variable
    variable = new_value                        # change a variable

Some useful commands you can use on the debugger:

    c or continue     # Continue running the program
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

    app:
        settings:
            debug: true

Or use it from the command line:

    gramex --settings.debug=true

**This uses a lot of CPU**. It also serves tracebacks on error. Do not enable
this on production systems.

## Profiling

`gramex.debug` provides support for timing and line profiling.

### Timer

`timer()` prints the time since last called. For example:

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
function. For example:

    @lineprofile
    def function(handler):
        # ... your code here...

prints line-by-line statistics about the function.
