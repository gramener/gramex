---
title: Finding slow code
prefix: Tip
...

The first step to optimising code is finding slow code.

Gramex 1.x has two functions that help with this.

## timer

The first is [gramex.debug.timer()](../debug/#timer).
It prints the time since its last call. You can introduce it between any two
lines to see how fast it runs. Here is a simple example:

    :::python
    from gramex.debug import timer

    def calc():
        timer('start')
        some_code()
        timer('ran some_code()')

This prints the following message on the log:

    I 05-May 08:16:38 debug:54 0.102s start [module.function:56]
    I 05-May 08:16:38 debug:54 0.012s ran some_code() [module.function:58]

## lineprofile

The second is [gramex.debug.lineprofile](../debug/#line-profile) - a decorator
that prints the time taken for each line of a function every time it is called.

For example:

    :::python
    import pandas as pd
    from gramex.debug import lineprofile

    @lineprofile
    def calc():
        data = pd.Series([x*x for x in range(1000)])
        diff = data.diff()
        acf = data.autocorr()
        return acf

When we run `calc()`, it prints the timing of each line:

    :::python
    Timer unit: 3.52616e-07 s

    Total time: 0.00198735 s
    File: <ipython-input-8-af6a7bd543d9>
    Function: calc at line 4

    Line #      Hits         Time  Per Hit   % Time  Line Contents
    ==============================================================
         4                                           @lineprofile
         5                                           def calc():
         6      1001         3023      3.0     53.6      data = pd.Series([x*x for x in range(1000)])
         7         1          613    613.0     10.9      diff = data.diff()
         8         1         1998   1998.0     35.5      acf = data.autocorr()
         9         1            2      2.0      0.0      return acf

## Remember

These functions work even when you're not running a Gramex server. You can use
them in ANY `Python` program or `IPython` script.
