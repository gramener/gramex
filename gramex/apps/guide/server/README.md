---
title: Gramex is a web server
prefix: Server
...

Gramex a data visualization server written in Python and JavaScript.

[TOC]

## Creating Gramex apps

When you run Gramex using `gramex` or `python -m gramex`, it starts a web server
at port 9988. This opens a welcome screen with a link to this guide.

Gramex's behaviour is controlled by a [YAML](http://yaml.org/spec/1.2/spec.html)
file called `gramex.yaml`. Here is the [full configuration](../final-config) for
this guide.

To start off, create a `gramex.yaml` with the lines shown below and run
`gramex`from there. You will see a list of files in that folder.

    :::yaml
    app:
        browser: /

Now run `gramex` (or `python -m gramex`) from the folder with `gramex.yaml`. You
should see a list of files in that folder. (You may need to press Ctrl-R or
Ctrl-F5 to refresh the page.)

If your folder has an `index.html` file, it is displayed instead of the
directory listing. You can now create static web applications with no additional
configuration.

Here is a [sample directory listing](static/).


## Gramex 0.x changes

If you're familiar with [Gramex 0.x](https://learn.gramener.com/docs/server),
Gramex 1.x is similar, but it doesn't display HTML files by default. To mimic
the behaviour, use the following `gramex.yaml`:

    :::yaml
    url:
      templates:                              # A unique name for this handler
          pattern: /(.*)                      # All URLs beginning with /
          handler: FileHandler                # Handler used
          kwargs:                             # Options to the handler
              path: .                         #   path is current dir
              default_filename: index.html    #   / becomes /index.html
              index: true                     #   display file list if index.html missing
              template: '*.html'              # Transform all .html files

Now, any `.html` file will be treated as a template, similar to Gramex 0.x. But
there are some key differences:

1. `file.html` was be rendered at `/file` as well as `/file.html` by Gramex 0.x.
   Gramex 1.x will only render at `/file.html`.
2. Gramex 0.x supported a non-standard `{% code %} ... {% end %}` template tag.
   Gramex 1.x only supports standard [Tornado templates][tornado-templates].
3. Gramex 0.x had a variety of server-side visualisations.
   Gramex 1.x only supports client-side visualisations.

[tornado-templates]: http://tornado.readthedocs.io/en/stable/template.html
