---
title: Function reloading
prefix: Tip
...

Gramex 1.19 has a number of powerful new features. The most useful of these, perhaps, is reloading.

So far, you needed to restart Gramex if you changed your `FunctionHandler` Python code. From now on, it auto-reloads.

Try it. Create a `FunctionHandler`. Change the Python script. Reload the output. You should see the result change immediately.

This is especially useful when debugging. If your function isn't working, just add a few `print()` statements in-between to see where the problem is.

Or you could add a `pdb.set_trace()` and debug it mid-way.
