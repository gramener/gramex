---
title: Quickstart Guide
prefix: tutorial
...

[TOC]

## Introduction

This tutorial is meant to guide developers along the process of creating a basic dashboard in gramex and is aimed primarily at new hires.
Complete code examples for any of the sections can be found under appropriate directories in this [repository](https://code.gramener.com/karmanya.aggarwal/quickstart/)

## Business Case

This tutorial follows a hypothetical company `X-MEDIA` which attempts to extract pertinent news and perform sentiment analysis on articles that could impact their customers' reputation.

### Problem Definition
- Develop a Data Visualization solution for a given X-Media dataset using gramex based on customer needs.

## Installing Gramex

- Install [Anaconda](https://www.anaconda.com/download/) 5.1 or higher on the machine
- Install [node.js](https://nodejs.org/en/) 8 or later. Then run `npm install -g yarn`. This step is required for UI components and built-in apps.
- `PATH setup` Anaconda by default asks to add PATH in environment variables.

![picture](img/path1.png)

- While installing `NodeJS`, be sure to keep track of the directory in which its installed; typically `C:/Program Files/nodejs/node` and ensure to add it to the system path. 

![picture](img/envi.png)

- If you are using MAC install [Xcode](https://idmsa.apple.com/IDMSWebAuth/login?appIdKey=891bd3417a7776362562d2197f89480a8547b108fd934911bcbea0110d07f757&path=%2Fdownload%2F&rv=1)

### Gramex Installation on Windows/Linux

- After satisfying  the above requirements in `Before you start` start installing gramex on your local machine.
- `Step 1`: Open Command prompt (or) Terminal
- `Step 2`: Run `pip install --verbose gramex`. Replace `gramex` with `gramex==1.32` for version 1.32 or later version.

```console
(gramexnew) λ pip install --verbose gramex
Config variable 'Py_DEBUG' is unset, Python ABI tag may be incorrect
Config variable 'WITH_PYMALLOC' is unset, Python ABI tag may be incorrect
Collecting gramex
  1 location(s) to search for versions of gramex:
  * https://pypi.python.org/simple/gramex/
  Getting page https://pypi.python.org/simple/gramex/
  Looking up "https://pypi.python.org/simple/gramex/" in the cache
  Current age based on date: 14
  Freshness lifetime from max-age: 600
  Freshness lifetime from request max-age: 600
  The response is "fresh", returning cached response
  600 > 14
  Analyzing links from page https://pypi.python.org/simple/gramex/
    Found link https://pypi.python.org/packages/a9/61/8051be1a0f3ab356a96ffcc6899059ef8ad7cb7413991d40333c8382260f/gramex-1.30.0.2.tar.gz#md5=975ff8c2f8e560d8a975bd9b1873eb45 (from https://pypi.python.org/simple/gramex/), version: 1.30.0.2
    Found link https://pypi.python.org/packages/93/b0/9229e85eca4a4475eeef60bcfc5f13711a932bebb79f98097f826a24e466/gramex-1.31.0.tar.gz#md5=2ed24830d3f552045e660be8f1f6f680 (from https://pypi.python.org/simple/gramex/), version: 1.31.0
    Found link https://pypi.python.org/packages/cb/e2/d658d69fb27f99457420dbfcbdd7aceb370a3c30f738f44636fe2cfa68d9/gramex-1.32.0.tar.gz#md5=378b8e4f030f0da25e5771f447dd042e (from https://pypi.python.org/simple/gramex/), version: 1.32.0
  Using version 1.32.0 (newest of versions: 1.30.0.2, 1.31.0, 1.32.0)
```

- `Step 3`: After successful installation Run `gramex` on command prompt (or) Terminal
- Log of actual request triggered along with underlying or supporting requests are displayed in the console.

```console
D:\tmp
(gramex) λ gramex
INFO    15-Apr 13:40:32 install Gramex 1.32.0 | guide --browser=/welcome | d:\anaconda\envs\gramex\lib\site-packages\gramex\apps\guide | Python 2.7.14 |Intel Corporation| (default, Feb 12 2018, 00:38:32) [MSC v.1500 64 bit (AMD64)]
WARNING 15-Apr 13:40:32 config Missing config: C:\Users\Gramener\AppData\Local\Gramex Data\mail\gramexmail.yaml
WARNING 15-Apr 13:40:33 watcher watch directory C:\Users\Gramener\AppData\Local\Gramex Data\mail does not exist
INFO    15-Apr 13:40:33 config No config found: C:\Users\Gramener\AppData\Local\Gramex Data\mail\gramexmail.yaml
INFO    15-Apr 13:40:34 __init__ Initialising schedule:gramex_update
INFO    15-Apr 13:40:34 __init__ Initialising schedule:create-user-database
INFO    15-Apr 13:40:37 __init__ Initialising schedule:data-setup-flags
INFO    15-Apr 13:40:37 dbsetup database.sqlite3 has flags table with data
INFO    15-Apr 13:40:37 __init__ Initialising schedule:data-setup-points
INFO    15-Apr 13:40:37 __init__ Initialising schedule:apps/logviewer-zxyfQ
INFO    15-Apr 13:40:38 __init__ Initialising schedule:run-on-startup
INFO    15-Apr 13:40:38 schedule:run-on-startup Scheduled msg (on startup)
INFO    15-Apr 13:40:38 __init__ Initialising schedule:run-every-hour
INFO    15-Apr 13:40:39 sqlitedict opening Sqlite table u'user' in C:\Users\Gramener\AppData\Local\Gramex Data\auth.user.db
INFO    15-Apr 13:40:39 capturehandler Pinging chromecapture.js at http://localhost:9900/
INFO    15-Apr 13:40:39 capturehandler Pinging chromecapture.js at http://localhost:9900/
d:\anaconda\envs\gramex\lib\site-packages\h5py\__init__.py:36: FutureWarning: Conversion of the second argument of issubdtype from `float` to `np.floating` is deprecated. In future, it will be treated as `np.float64 == np.dtype(float).type`.
  from ._conv import register_converters as _register_converters
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-email
WARNING 15-Apr 13:40:40 __init__ alert: alert-email: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-email has no schedule nor startup
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-html
WARNING 15-Apr 13:40:40 __init__ alert: alert-html: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-html has no schedule nor startup
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-markdown
WARNING 15-Apr 13:40:40 __init__ alert: alert-markdown: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-markdown has no schedule nor startup
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-content-file
WARNING 15-Apr 13:40:40 __init__ alert: alert-content-file: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-content-file has no schedule nor startup
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-images
WARNING 15-Apr 13:40:40 __init__ alert: alert-images: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-images has no schedule nor startup
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-attachments
WARNING 15-Apr 13:40:40 __init__ alert: alert-attachments: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-attachments has no schedule nor startup
INFO    15-Apr 13:40:40 __init__ Initialising alert: alert-templates
WARNING 15-Apr 13:40:40 __init__ alert: alert-templates: using first email service: alert-gmail
WARNING 15-Apr 13:40:40 scheduler schedule:alert-templates has no schedule nor startup
INFO    15-Apr 13:40:40 config No config found: C:\Users\Gramener\AppData\Local\Gramex Data\mail\gramexmail.yaml
INFO    15-Apr 13:40:40 __init__ Listening on port 9988
INFO    15-Apr 13:40:40 __init__ Opening http://127.0.0.1:9988/welcome in WindowsDefault browser
INFO    15-Apr 13:40:41 __init__ 304 GET /welcome (127.0.0.1) 16.00ms welcome
INFO    15-Apr 13:40:41 capturehandler Starting chromecapture.js via node "d:\anaconda\envs\gramex\lib\site-packages\gramex\apps\capture\chromecapture.js" --port=9900
INFO    15-Apr 13:40:41 capturehandler Starting chromecapture.js via node "d:\anaconda\envs\gramex\lib\site-packages\gramex\apps\capture\chromecapture.js" --port=9900
INFO    15-Apr 13:40:41 __init__ 304 GET /background.jpg (127.0.0.1) 4.00ms markdown
WARNING 15-Apr 13:40:42 __init__ 404 GET /favicon.ico (127.0.0.1) 40.00ms markdown
INFO    15-Apr 13:40:42 capturehandler Pinging chromecapture.js at http://localhost:9900/
INFO    15-Apr 13:40:42 capturehandler node.js: v8.9.4 chromecapture.js: 1.1.0 port: 9900 pid: 3884 live (pid=3884)
```

- `Step 4`: You will see a blue screen with text `Welcome to Gramex` as output. Now you have gramex installed on your local machine.

![picture](img/output.png)

- `Step 5`: In case you get 404 errors for `localhost:9988/welcome` or the page doesn't render properly, run `gramex setup --all` to ensure all the nodejs modules are installed. 
## Folder Structure of a Simple Gramex Dashboard

### Gramex Init

- `Step 1` Create a new folder with `project_name` on your local machine.
- `Step 2` Run `gramex init` on your preferred terminal (command prompt/cmder/terminal/GitBash etc.)
- It is the initial stage of your Data Visualization project. `gramex init`  will setup the necessary project linting files and default files.

List of files generated are below.

- [`.editorconfig`](#editorconfig)
- [`.eslintrc.js`](#eslintrcjs)
- [`.flake8`](#flake8)
- [`.gitlab-ci.yml`](#gitlab-ciyml)
- [`.gitignore`](#gitignore)

In addition, it generates a simple boilerplate for

- [`gramex.yaml`](#gramexyaml)
- [`index.html`](#indexhtml)
- [`readme.md`](#readmemd)

### .editorconfig

It helps developers define and maintain consistent coding styles between different editors and IDEs. The EditorConfig project consists of a file format for defining coding styles and a collection of text editor plugins that enable editors to read the file format and adhere to defined styles. EditorConfig files are easily readable and they work nicely with version control systems.

```
# Style 1:
if (hours < 24 && minutes < 60 && seconds < 60) {
    return true;
} else {
    return false;
}
--------------------------------------------------------------------------------------------
# Style 2:
if (hours < 24 && minutes < 60 && seconds < 60)
{
    return true;
}
else
{
    return false;
}
--------------------------------------------------------------------------------------------
# Style 3:
if  ( hours   < 24
   && minutes < 60
   && seconds < 60
)
{return    true
;}         else
{return   false
;}


```

- When we look into the style1 and style2 code is easy to understand because They used consistent style in writing the code. Similarly `gramex` also has its own programming style which will be defined in `.editorconfig`

The supported Properties for `.editorconfig` are:

- Indent style.
- Indent size.
- End of line.
- Trim trailing whitespace.
- Insert final newline.

### .eslintrc.js

It is completely configurable for javascript, meaning you can turn off every rule and run only with basic syntax validation, or mix and match the bundled rules and your custom rules which makes your project perfect.

There are several pieces of information that can be configured:

- `Environments` which environments your script is designed to run in. Each environment brings with it a certain set of predefined global variables.
- `Globals` the additional global variables your script accesses during execution.
- `Rules` which rules are enabled and at what error level.

### .flake8
- We can declare the parameters to lint Python code in the application.
- This helps in prevent things like syntax errors, typos, bad formatting, incorrect styling etc.,

### .gitlab-ci.yml
- All the projects build on top of gramex are deployed in to gitlab.
- This `.gitlab-ci.yml` uses a [`YAML`](http://yaml.org/spec/1.2/spec.html) file for project configuration.

### .gitignore
- This helps the gramex user to ignore files that should not be committed.
- spcify the files that you would like to ignore.
- `example` file containing  Passwords, Private information.

### .htmllintrc
- In `htmllintrc` the user can define certain parameters so that It statically checks your documents for common errors in HTML code.

### gramex.yaml
- Gramex’s behaviour is controlled by a [`YAML`](http://yaml.org/spec/1.2/spec.html) file called gramex.yaml
- `gramex init` creates a `gramex.yaml` file which contains the below code as default

```
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml    # Import the UI components
    YAMLURL: $YAMLURL/ui/               # ... at this URL
```

### index.html
- The code related to `html` will be written here.
- styling must be defined in bootstrap classes.

### README.md
- User can document the project workflow in this `markdown` file

## Configuration

Gramex is primarily configuration driven, and supports server configuration via YAML files.

Through a YAML file, developers define handlers, which trigger actions on receiving requests to the server at developer defined endpoints.
Handlers can be used to manipulate data and render files, draw charts/visualisations, allow for server side caching, configure the gramex web server, etc.

The `gramex.yaml` file serves as a base for all server configurations in a gramex app or dashboard.
for example -
```yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml    # Import the UI components
    YAMLURL: $YAMLURL/ui/               # ... at this URL
url:
  quickstart/home:                      # name of the endpoint
    pattern: /$YAMLURL/                 # The path/URL at which the request should be sent.
    handler: FileHandler                # The type of custom handler used
    kwargs:                             # Additional Parameters
      path: $YAMLPATH/index.html        # Which file to return.
```
This yaml configuration defines a single FileHandler endpoint.
FileHandler is used to render files or templates to the end user. In this case, on receiving a request to the homepage, gramex will return index.html.
`$YAMLURL` and `$YAMLPATH` are environment variables which store the url and path of the current yaml file respectively.

For the purpose of this tutorial, three endpoints are defined - a FileHandler to render the html page and a FormHandler to load and manipulate data.
the formhandler endpoint can be defined as follows -

```yaml
url:
  quickstart/formhandler:
      pattern: /$YAMLURL/alldata                                                 # The endpoint
      handler: FormHandler
      kwargs:
        url: 'mysql://root:root@localhost:3306/quickstart?charset=utf8'           # DB connect string
        query: select * from test_table where Dated >= '{start}' and Dated <='{end}' # DB Query
        table: select count(*) from test_table                   #(optional) Cache update condition
        modify: quickstart.catchall(data,handler)                # Function call
```
On receiving a request to the `/alldata` endpoint, Gramex, reads data via the SQL query, loads it into memory and calls the catchall function defined in `quickstart.py` passing it the loaded dataframe (data) and the tornado requesthandler (handler).
The curly braces in  `'{start}` and `'{end}'` imply that those values shall be picked up from the URL parameters.

Passing the requesthandler is important as it will allow the frontend to send additional data to the backend.

the `table` key is used to cache the data retrieved by the query on the server, in this case, it will update the cached data every time the number of rows in the test table changes. This ensures that the dashboard will be relatively responsive for the client. The reason this example uses only a single formhandler endpoint instead of multiple, is that the gramex will cache the data retrieved by formhandler on the server side, for a more responsive dashboard.

Having saved this configuration to gramex.yaml in the folder, visiting [this link](http://localhost:9988/alldata?start=2018-03-07&end=2018-03-07&_format=table) will render the retreived data as an interactive table. Alternatively, Formhandler can return data in multiple formats.
![Formhandler Table Screenshot](img/fts.png)

Click [here](../config/) for more information about yaml configurations
and [here](../formhandler/) for more information about FormHandler.

Click [here](https://code.gramener.com/karmanya.aggarwal/quickstart/tree/master/config) to download a working example of the app.

Click [here](../) to see a list of all the custom handlers that gramex offers

## Scaffolding

The next step is to create a scaffolding of the dashboard, typically with inputs from the design team and front end engineers. The scaffolding is intended to display the rough structure of the webpage before charts and tables are added.

This is done simply in HTML and bootstrap, using as little custom css as possible.
Often templates are used to reduce the amount of front end code required - the G1 library (a JS library developed in-house) provides support for lodash templates, though gramex also supports Tornado Templates.

The UI component exposes a set of commonly used libraries (bootstrap, jquery, d3 etc) which allows
for developers to include these libraries without using a CDN, yarn/npm/bower etc.
Using it, requires a small modification to the gramex.yaml file to mount the ui component at a particular url.
```yaml
import:
  ui:
    path: $GRAMEXAPPS/ui/gramex.yaml    # Import the UI components
    YAMLURL: $YAMLURL/ui/               # ... at this URL
```
After which, libraries can be included as follows
```html
<link rel="stylesheet" href="ui/bootstraptheme.css">
<script src="ui/jquery/dist/jquery.min.js"></script>
<script src="ui/popper.js/dist/umd/popper.min.js"></script>
<script src="ui/bootstrap/dist/js/bootstrap.min.js"></script>
```

Click [here](../uicomponents/#libraries) for a list of all libraries included in UI Components
Click [here](https://code.gramener.com/cto/g1/blob/master/README.md) to see documentation for G1
Click [here](https://code.gramener.com/karmanya.aggarwal/quickstart/tree/master/scaffolding) to see a working example of the dashboard at this stage

## Data Validation/configuration driven charts

Once the scaffolding has been created, the data and scaffolding can be quickly validated via [formhandler tables](../formhandler/#formhandler-tables) or a configuration driven [charting library](../formhandler/#formhandler-charts) (Vega, Vega-lite, Seaborn and Vegam).

The advantage of populating the data with static/configuration driven charts is that it adds visualization capabilities to the dashboard without requiring any custom Javascript.
The only caveat is that the these charts/tables are currently not responsive.

For the purpose of this quickstart, first a vega-lite stacked bar chart will be created.
This requires a small modification to the ```gramex.yaml```
```yaml
quickstart/dataurl:
    pattern: /$YAMLURL/alldata
    handler: FormHandler
    kwargs:
      url: 'mysql://root:root@localhost:3306/quickstart?charset=utf8'
      query: select * from test_table where Dated >= '{start}' and Dated <='{end}'
      table: select count(*) from test_table
      modify: quickstart.catchall(data,handler)
      formats:
        stackbar:
          format: vega-lite  # Use Seaborn/Vega/Vega-lite/vegam
          spec:              # Defines the configurations for the vega-charts
            $schema: 'https://vega.github.io/schema/vega-lite/v2.json' # Constant for all vega-lite charts
            mark: bar
            width: 315       # Dimensions of the rendered svg
            height: 180
            encoding:        # which data
                x: {from: data, aggregate: count, field: Overall_Tonality, type: quantitative}
                y: {from: data, field: TagValue, type: nominal}
                color: {from: data, field: Overall_Tonality, type: nominal}
```
Here a format called stackbar is created for the FormHandler endpoint defined earlier. This particular spec defines a stacked bar chart which accepts the data loaded from the FormHandler (implicitly named `data`) and plots TagValue versus Overall_Tonality.

Now, the charts can be inserted in any html page/template via a simple `<script>` tag
```html
<div>
  <script src="alldata?start=2017-11-01&end=2017-11-21&chart=people&_format=stackbar"></script>
</div>
```
thus, the script will make a request to the alldata endpoint, passing a start date, end date and chart type to server via URL Parameters which can be accessed in the backend through the handler object. `_format=stackbar` tells gramex that the output needs to be rendered as a stacked bar chart, via the spec defined in the yaml.
Finally, in order to use vega charts, a js file needs to be included.
```html
<script src="https://cdn.jsdelivr.net/npm/vega-lite@2.3.1/build/vega-lite.min.js"></script>
```

In a similar vein, modifications are required to render the data using formhandler tables - the formhandler table app needs to be imported and mounted in the YAML
```yaml
import:
  table:
    path: $GRAMEXPATH/apps/formhandler/gramex.yaml
    YAMLURL: $YAMLURL
```
The G1 Library needs to be included
```html
<script type="text/javascript" src="ui/g1/dist/g1.min.js"></script>
```

finally, the html needs to be updated to render the actual table.
```html
<!-- first the element is inserted in place -->
<div class="formhandler" data-src="alldata?start=2017-11-01&end=2017-11-21"></div>
<!-- then the table is rendered -->
<script>
  ('.formhandler').formhandler()
</script>
```
Notice how the endpoint referenced by the formhandler table is very similar to the one passed to vega-lite, this is due to the fact that both should load the same data, just in different formats.
Additional parameters can be passed to the formhandler function - see a list in the [API documentation](https://code.gramener.com/cto/g1/#formhandler)

A working example of the dashboard at this stage can be found [here](https://code.gramener.com/karmanya.aggarwal/quickstart/tree/master/static-data)

Some backend modifications are also required to ensure that the data returned from Formhandler is in the format that each of the charts/tables expect.

## Backend Data Transformation
All the data visualization projects use python and its stack to filter data in the backend.

YAML files support python/pandas functions intended to transform the data as required, however for involved transformations, it's good practise to include a python file defining required functions and calling appropriate functions from the YAML.

for example, the catchall function that was first mentioned in the configuration sections is defined as follows -

```python
def catchall(data, handler):
    ''' Calls the appropriate function to return a particular data format'''
    if handler.get_arguments('chart'):
        chart = handler.get_arguments('chart')[0]
        data = prep_df(data)
        if chart == "sent":
            return sentiment_data(data, handler)
        elif chart== "people":
            return people_in_news(data,handler)
        elif chart == "category":
            return category_data(data,handler)
        elif chart == "issues":
            return issues_data(data,handler)
        elif chart == "publications":
            return publication_data(data,handler)
        elif chart == "authors":
            return author_data(data,handler)
    else:
        return data
```
Thus this function looks for a type of chart sent via the URL parameters, and if present calls the appropriate transformation function or just returns the loaded data if no type of chart is present.

`handler` is a tornado request handler object, which is used to access URL query parameters.

The data loaded by the Formhandler endpoint can also be implicitly passed to the function, as a pandas dataframe called 'data'.

for an example of the complete quickstart.py file click [here](https://code.gramener.com/karmanya.aggarwal/quickstart/blob/master/static-data/quickstart.py)
or look at the quickstart.py file in the interaction section of this tutorial, as the data format required for Vega-lite and the custom interactive charts is slightly different.

## Interactivity/Drilldowns and Filtering

In order to facilitate interactive charts or charts which require a large amount of customization, often d3.js is used. In this process, developers are heavily encouraged to follow the principles of component reuse - such that if a chart is created for one project, it should be written in such a way that it can be reused across multiple projects without much extra work.

As previously mentioned, the UI components library includes d3.js so the first step is to include it  inside the html and then javascript can be used to load data and pass it to various chart components.
```html
<script src="ui/d3/build/d3.min.js"></script>
<!-- after which we can use JS to load data from the endpoint using AJAX calls and pass it to various charts -->
<script>
$.getJSON(
      "alldata?chart=people" +
        "&start=" +
        start +
        "&end=" +
        end +
        "&array_tonality=" +
        JSON.stringify(array_tonality) +
        "&lang_array=" +
        JSON.stringify(language_sel) +
        "&cat_array=" +
        JSON.stringify(categories) +
        "&auth_array=" +
        JSON.stringify(authors) +
        "&pub_array=" +
        JSON.stringify(publishers) +
        "&people_in_news=" +
        JSON.stringify(people_in_news) +
        "&issues=" +
        JSON.stringify(issues),function(data){
          chart(data)
        }
</script>
```
In order to facilitate filtering and drilldowns, the G1 library provides a urlfilter function which updates url parameters in place - combined with formhandler, this allows for complicated filterign with very little custom code written. (Note - this is WIP, @karmanya.aggarwal is working on incorporating urlfilter and rewriting the JS to reduce duplication)

For an example of the dashboard in it's current state click [here](https://code.gramener.com/karmanya.aggarwal/quickstart/tree/master/complete)


## Screenshots via CaptureHandler

Gramex has a feature to export your visuals in the following formats

- `PDF`
- `PNG`
- `PPTX`
- `JPG`

Follow the steps below to capture the dashboard

- Configure the YAML file so that with required parameters
- `engine` browser that used to run the application `chrome` is the recommended
engine.
- `port` use port other than gramex port
- `timeout` maximum time required to receive server response.

```
url:
    capture:
        pattern: /$YAMLURL/capture
        handler: CaptureHandler
        kwargs:
            engine: chrome
            port: 9901
            timeout: 20
```

- Every screenshot is exported using a click action element for CaptureHandler.
- Add a `Button` element that match with the export format.

```
<button class = "btn dropdown-toggle" type="button" data-toggle="dropdown">
<img src="ppt.svg"></button>
<ul class="dropdown-menu dropdown-right"
<a href="capture?ext=pdf?orientation=landscape?delay=1000">PDF screenshot</a>
<a href="capture?ext=png?orientation=landscape?delay=1000">PNG screenshot</a>
<a href="capture?ext=jpg?orientation=landscape?delay=1000">JPG screenshot</a>
<a href="capture?ext=pptx?orientation=landscape?delay=1000">PPTX screenshot</a>
</ul>
```

- Encode URLs in javascript to take screenshot in any drilldown.

```js
	$('.screenshot').attr('href', 'capture' +
    '?url=' + encodeURIComponent(url) +
    '&header=' + encodeURIComponent(header))
```
