---
title: Cache calculations in Gramex
prefix: Tip
...

It's a bad idea to run calculations after loading cached data.

    :::python
    # This code is wrong:
    data = gramex.cache.open(data_file, 'csv')
    result = calculations(data)

There is no point re-computing the data unless `data_file` has changed. Instead,
[gramex.cache.open](https://learn.gramener.com/gramex/gramex.html#gramex.cache.open)
supports a `transform=` parameter. Do the following:

    :::python
    result = gramex.cache.open(data_file, 'csv', transform=calculations)

This will re-run calculations only if the data_file has changed.

You can return multiple calculations, including the dataset, either as a tuple or as a dict. For example:

    :::python
    # Return multiple calculations as a tuple
    data, calc1, calc2 = gramex.cache.open(data_file, 'csv', transform=calculations)

or...

    :::python
    # Return a dict of calculations
    result = gramex.cache.open(data_file, 'csv', transform=calculations)
    result['data']     # has the data
    result['calc1']    # has the first calculation results, and so on
