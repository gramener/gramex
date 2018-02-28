---
title: Store data in data files, not Python files
prefix: Tip
...

Store data in data files, not Python files.

This lets other people (analysts, client IT teams, administrators) edit the data
- especially if they cannot program.

You're a good programmer when you stop thinking *How to write code* and begin
thinking *How will people use my code*.

## Data in JSON

A structure such as this:

    :::python
    lookup = {
        'l1': dict(file='PSU_l1.csv',        row=-1),
        'l2': dict(file='PSU_l2.csv',        row=-1),
        'l3': dict(file='PSU_Personnel.csv', row=0),
    }

... is better stored as `config.json`:

    :::json
    {
        "l1": {"file": "PSU_l1.csv", "row": -1},
        "l2": {"file": "PSU_l2.csv", "row": -1},
        "l3": {"file": "PSU_Personnel.csv", "row": 0}
    }

... and read via:

    :::python
    import json
    lookup = json.load(open('config.json'))

## Data in YAML

YAML is be more intuitive less error-prone. There are no trailing commas or
braces to get wrong. It also supports data re-use via [anchors][anchors].

    :::yaml
    l1:
        file: PSU_l1.csv
        row: -1
    l2:
        file: PSU_l1.csv
        row: -1
    l3:
        file: PSU_Personnel.csv
        row: 0

You can read these via:

    :::python
    import yaml
    lookup = yaml.load(open('config.yaml'))

[anchors]: http://camel.readthedocs.io/en/latest/yamlref.html#anchors
