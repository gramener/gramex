---
title: DataHandler for flat files and databases
prefix: Tip
...

You can use `DataHandler` to fetch data from CSV and remote databases using the driver argument as below:

- for flat files, use `driver: blaze`
- for databases, use `driver: sqlalchemy`

Here's a 3 minute video on its working: [https://asciinema.org/a/FWCjuoRJD3zbAl9OXL2W3fY4C](https://asciinema.org/a/FWCjuoRJD3zbAl9OXL2W3fY4C)

**Modifying databases**

It can also be used to add/update/delete records in databases (with `POST`, `PUT`, `DELETE` options).

Detailed documentation: [https://learn.gramener.com/guide/datahandler/](https://learn.gramener.com/guide/datahandler/)
