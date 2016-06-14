title: Gramex is a web server

When you run Gramex using `gramex` or `python -m gramex`, it starts a web server
at port 9988. This opens a welcome screen with a link to this guide.

Gramex's behaviour is controlled by a [YAML](http://yaml.org/spec/1.2/spec.html)
file called `gramex.yaml`. Here is the [full configuration](/final-config) for
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
