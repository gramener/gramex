title: Gramex is a web server

When you run Gramex using `gramex` or `python -m gramex`, it starts a web server at port 9988.

Gramex's behaviour is controlled by a [YAML](http://yaml.org/spec/1.2/spec.html)
file called `gramex.yaml`. Here is the full configuration for this guide as an
example: [gramex.yaml](../config)

To start off, create a `gramex.yaml` with the lines shown below and run
`gramex`from there. You will see a list of files in that folder.

    app:
        browser: True

If your folder has an `index.html` file, it is displayed instead of the
directory listing.

You can include other files from here. This page includes an image at
[static/image.svg](static/image.svg).

![static image](static/image.svg)

Below are the contents of [static/plain.txt](static/plain.txt): a plain text file.

<iframe src="static/plain.txt"></iframe>
