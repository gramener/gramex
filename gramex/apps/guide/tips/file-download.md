---
title: File download using FileHandler
prefix: Tip
...

Download a File using FileHandler

    :::python
    url:
        project/file-download:
            pattern: /$YAMLURL/data
            handler: FileHandler
            kwargs:
            path: data.csv
            headers:
                Content-Type: text/csv
                Content-Disposition: attachment;filename=data.csv

`MIME` type `text/csv` sets the type for CSV files.

Further, one can trigger the download using FunctionHandler (for content generated with custom logic) with

    :::python
    handler.set_header('Content-Type', 'text/csv')
    handler.set_header('Content-Disposition', 'attachment; filename='+your_file)
