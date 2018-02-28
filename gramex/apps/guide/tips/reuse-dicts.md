---
title: Look up values in a dict to handle variations
prefix: Tip
...

This code reads 3 datasets:

    :::python
    data_l1 = pd.read_csv('PSU_l1.csv')
    data_l2 = pd.read_csv('PSU_l2.csv')
    data_l3 = pd.read_csv('PSU_l3.csv')

Based on the user's input, the last row of the relevant dataset is picked:

    :::python
    if form_type == "l1":
        result = data_l1[:-1]
    elif form_type == "l2":
        result = data_l2[:-1]
    elif form_type == "l3":
        result = data_l3[:-1]

It's not trivial to replace this with a loop or a lookup.

**Data structures avoid duplication**.

Instead of loading into 4 datasets, use:

    :::python
    data = {
        level: pd.read_csv('PSU_' + level + '.csv')
        for level in ['l1', 'l2', 'l3']
    }
    result = data[form_type][:-1]

This cuts down the code, and it's easier to add new datasets.

## But inputs are not consistent

The third file alone is named `PSU_Personnel.csv` instead of `PSU_l3.csv`. But we
want to map it to `data['l3']`, because that's how the user will request it.

So use a mapping:

    :::python
    lookup = {
        'l1': 'PSU_l1.csv',
        'l2': 'PSU_l2.csv',
        'l3': 'PSU_Personnel.csv',  # different filename
    }
    data = {key: pd.read_csv(file) for key, file in lookup.items()}
    result = data[form_type][:-1]

## But operations are different

For `PSU_Personnel.csv`, we want to pick the first row, not the last row.

So add the row into the mapping as well:

    :::python
    lookup = {                             # Define row for each file
        'l1': dict(file='PSU_l1.csv',        row=-1),
        'l2': dict(file='PSU_l2.csv',        row=-1),
        'l3': dict(file='PSU_Personnel.csv', row=0),
    }
    data = {key: pd.read_csv(info['file']) for key, info in lookup.items()}
    result = data[form_type][:lookup[form_type]['row']]

## But operations are very different

For `PSU_l1.csv`, we want to sort it.
For `PSU_l2.csv`, we want to fill empty values.

Then use functions to define your operations.

    :::python
    lookup = {
        'l1': dict(file='PSU_l1.csv', op=lambda v: v.sort()),
        'l2': dict(file='PSU_l2.csv', op=lambda v: v.fillna('')),
        'l3': dict(file='PSU_Personnel.csv', op=lambda v: v),
    }
    data = {key: pd.read_csv(info['file']) for key, info in lookup.items()}
    result = lookup[form_type]['op'](data[form_type])

The functions need not be `lambda`s. They can be normal multi-line functions.
