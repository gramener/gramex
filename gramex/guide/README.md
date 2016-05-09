title: Gramex Guide
classes: toc

## [Install Gramex](install/)

**Exercise**: Install Gramex on your system and run `gramex`.

## [Gramex is a web server](server/)

**Exercise**: Create a `gramex.yaml` file in any directory and browse its contents.

## [Configurations control Gramex](config/)

**Exercise**: Create a `gramex.yaml` that runs Gramex on port 80 and logs every request to a file.

## [Gramex runs Python functions](functionhandler/)

**Exercise**: Make </greet> show "Hello {name}" when a `?name=` parameter is passed.

## [Gramex renders files](filehandler/)

**Exercise**: Make `/blog/` render a simple Markdown-based blog.

## [Gramex connects to data](datahandler/)

**Exercise**: Load a dataset into MySQL or PostgreSQL, and create a DataHandler that exposes that table.

## [Gramex writes data](jsonhandler/)

**Exercise**: TBD

## [Gramex runs processes](processhandler/)

**Exercise**: Display the results of `git log` on a git repository.

## [Gramex authentication](auth/)

**Exercise**: Make gramex-guide without authetication and create google-auth only to `/blog/`.

## [Gramex caches requests](cache/)

**Exercise**: TBD

## [Gramex charts](chart/)

**Exercise**: Draw a simple pie chart using data from DataHandler.

## [Gramex can schedule tasks](scheduler/)

**Exercise**: Make Gramex log the time into <code>time.log</code> on startup, and every 2 minutes.

## [Gramex watches files](watch/)

**Exercise**: Make Gramex log a message when a file is changed.

## [Deployment patterns](deploy/)

**Exercise**: TBD
