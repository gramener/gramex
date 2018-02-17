---
title: Download Data
prefix: Tip
...

[gramex.data.download](https://learn.gramener.com/gramex/gramex.html#gramex.data.download) lets users download a DataFrame inside a FunctionHandler.

For example:

    :::python
    def download_as_excel(handler):
        handler.set_header('Content-Type', 'application/' +
            'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        handler.set_header('Content-Disposition', 'attachment;filename=data.xlsx')
        return gramex.data.download(dataframe, format='xlsx')

You can choose to download as CSV, JSON, HTML, or you can construct a template to render in any other format (e.g. XML, custom dashboard, etc.)

This is the same functionality used in [FormHandler formats](../formhandler/#formhandler-formats).

You can also download multiple dataframes. Pass a dictionary of dataframes. This is rendered in Excel as a multi-sheet file, and as multiple tables in CSV and HTML, and as a dictionary of datasets in JSON.

See the section on [FormHandler multiple datasets](../formhandler/#formhandler-multiple-datasets) for examples of the output.
