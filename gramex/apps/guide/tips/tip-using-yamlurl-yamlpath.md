title: Using YAMLURL

Suppose you create a gramex.yaml like this:

url:
  app-home:
    pattern: /          # The home page
    handler: ...
This works fine locally. But when you deploy it on [uat.gramener.com/app/](uat.gramener.com/app/), it won't work. That's because you've mapped the URL /, not /app/.

Since you don't know beforehand which directory you'll be deploying the app, it's best to use pattern: /$YAMLURL/ instead. $YAMLURL the relative URL to the current gramex.yaml location. In your local machine, this becomes /. On the server, this becomes /app/.

You also need this in [redirection URLs](https://learn.gramener.com/guide/config/#redirection). See this example:

url:
  auth/simple:
    pattern: /$YAMLURL/simple
    handler: SimpleAuth
    kwargs:
      credentials: {alpha: alpha}
      redirect: {url: /$YAMLURL/}        # Note the $YAMLURL here
Using /$YAMLURL/ redirects users back to this app's home page, rather than the global home page (which may be uat.gramener.com/.)

Tips:

/$YAMLURL/ will always have a / before and after it.
pattern: must always start with /$YAMLURL/
url: generally starts with /$YAMLURL/
Using YAMLPATH

$YAMLPATH is very similar to $YAMLURL. It is the relative path to the current gramex.yaml location.

When using a FileHandler like this:

url:
  app-home:
    pattern: /                  # This is hard-coded
    handler: FileHandler
    kwargs:
      path: index.html          # This is hard-coded
... the locations are specified relative to where Gramex is running. To make it relative to where the gramex.yaml file is, use:

url:
  app-home:
    pattern: /$YAMLURL/
    handler: FileHandler
    kwargs:
      path: $YAMLPATH/index.html        # Path is relative to this directory
Tips:

$YAMLPATH/ will never have a / before it, but generally have a / after it
path: must always start with a $YAMLPATH/
url: for DataHandler or QueryHandler can use it for SQLite or Blaze objects. For example, url: sqlite:///$YAMLPATH/sql.db