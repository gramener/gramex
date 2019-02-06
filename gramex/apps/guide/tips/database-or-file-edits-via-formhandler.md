---
title: Database or file edits via FormHandler
prefix: Tip
...

It is now easy to update or modify data sources via FormHandler. FormHandler now supports `PUT`, `POST` and `DELETE` methods in addition to `GET`. These can be done via `HTML` forms or `AJAX` requests.

**POST** - [Insert records](../formhandler/#formhandler-post)

    :::html
    <!-- flags.csv has ID, Name, Text and many other fields -->
    <form action="flags-add" method="POST" enctype="multipart/form-data">
      <label for="ID">ID</label>     <input type="text" name="ID" value="XXX">
      <label for="Name">Name</label> <input type="text" name="Name" value="New country">
      <label for="Text">Text</label> <input type="text" name="Text" value="New text">
      <input type="hidden" name="_xsrf" value="{{ handler.xsrf_token }}">
      <button type="submit" class="btn btn-submit">Submit</button>
    </form>

This saves a new record in flags.csv. FormHandler picks the input field name and value attributes.

**PUT via AJAX** - [Update current records](../formhandler/#formhandler-put)

    :::js
    // flags.csv has ID, Name, Text and many other fields
    $.ajax('flags-edit', {
      method: 'PUT',
      headers: xsrf_token,      // See documentation on XSRF tokens
      data: {ID: 'XXX', Name: 'Country 1', Text: 'Text ' + Math.random()}
    })

Delete works similarly.

**Return value** - in all the cases, FormHandler returns the number of rows affected (inserted, deleted or updated).

## Required YAML configuration

In the `kwargs` section, mention the primary key on which you would like to perform the edit. It can also be a list of values.

    :::yaml
    id: ID        # Make ID the primary key

## Editing DataFrames

You can also use these methods via

- `gramex.data.insert`
- `gramex.data.update`
- `gramex.data.delete`

This works similar to `gramex.data.download` or `gramex.data.filter`. Check out `data.py` source code below for minimal params.

- **Current usage**: [EY admin RPA](https://code.gramener.com/ey/ey-admin/blob/master/rpa/ey_admin_rpa.yaml#L13)
- **Documentation**: This is well documented on the [guide for FormHandler](../formhandler/#formhandler-edits)
- **Source code**: Head to the [source code](https://github.com/gramener/gramex/blob/dev/gramex/data.py)
  (`insert`/`delete`/`update` methods in `data.py`) and how `FormHandler`
  [renders](https://github.com/gramener/gramex/blob/dev/gramex/handlers/formhandler.py) it,
  if you are interested.
