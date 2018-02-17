---
title: Automatically fixing Python build errors
prefix: Tip
...

You can use [autopep8](https://pypi.python.org/pypi/autopep8) to fix the most common Python build errors quickly. This is documented on the [wiki](https://learn.gramener.com/wiki/dev.html#fixing-build-errors).

The steps are simple: install `autopep8` and run it on your Python file.

    :::shell
    pip install autopep8
    autopep8 -iv --max-line-length 99 *.py

It doesn't fix all errors. But when checking the most common errors in the last 4 months, I find that 50-90% of the errors are auto-fixed.

This apart, the [wiki](https://learn.gramener.com/wiki/dev.html#fixing-build-errors)
also documents the most common errors this doesn't fix, and how to fix them.
