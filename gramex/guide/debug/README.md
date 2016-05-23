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
