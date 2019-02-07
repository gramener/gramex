---
title: R
prefix: R
...

[TOC]

To run R in Gramex, install [rpy2](https://rpy2.readthedocs.io/) first:

```bash
conda install rpy2          # Do not use pip. Gramex assumes you use conda
```

This installs a new R to the Anaconda PATH, ignoring the system R.

**Caution**: You'll have 2 `R`s in your system -- the Anaconda R and the system
R. Running `R` from the command line will run whichever is first in your PATH.
Installing a package in one **does not** install a package in the other.

Here is an example of a prime number calculation in R:

- [prime](prime): calculate prime numbers up to 100
- [prime?n=1000](prime?n=1000): calculate prime numbers up to 1,000

See the [Python source](rcalc.py) and the [R script](sieve.R).

## R commands

Call `gramex.ml.r('R expression')` to run an `R` command and return its result.

```python
import gramex.ml
total = gramex.ml.r('sum(c(1,2,3))')    # Add up numbers and return the result
```

Multi-line commands are allowed. The last line is returned.

```python
total = gramex.ml.r('''
x <- rnorm(10)          # Generate 10 random numbers
sum(x)                  # Add them up and return the value
''')
```

But **avoid multi-line commands**. [Run .R scripts](#r-scripts)
instead. This lets you re-use the scripts elsewhere, unit-test them, lint them,
etc. You also get editor syntax-highlighting.

Gramex runs a single R session. All variables are remembered across calls:

```python
gramex.ml.r('x <- rnorm(10)')           # R variable "x" has 10 random numbers
total = gramex.ml.r('sum(x)')           # "x" defined earlier can be used
gramex.ml.r('rm(x)')                    # Now "x" is deleted. Memory is released
```

## R scripts

Call `gramex.ml.r(path='script.R')` to source `script.R`.

[sieve.R](sieve.R) defines a prime number function
`sieve(n)`. To load it, use:

```python
gramex.ml.r(path='sieve.R')     # Loads relative to the Python file
gramex.ml.r('sieve(10)')        # Returns [2, 3, 5, 7] -- primes up to 10
```

Gramex loads `sieve.R` relative to the Python file that calls it. (But specify
an absolute path to play it safe.)

Scripts can source other scripts. For example:

```R
source('sieve.R', chdir=T)      # Always use chdir=T when using source()
sieve(n)
```

## R arguments

All keyword arguments passed to `gramex.ml.r()` are available as global
variables to the script. For example:

```python
>>> gramex.ml.r('rnorm(n, mean, sd)', n=3, mean=100, sd=20)
array([125.80012342, 104.30249101,  97.31857082])
```

In the script above, `rnorm(n)` uses the R variables `n`, `mean` and `sd`, which
are set by Gramex by passing keyword arguments.

Pandas Series are automatically converted into R vectors, and vice versa.

```python
>>> gramex.ml.r(
...     'pnorm(x, log.p=log)',          # Use variables x and log
...     x=pd.Series([0.2, 0.5, 1.0]),   # Pandas series converted into a vector
...     log=False,                      # Boolean values converted to R booleans
... )
array([0.57925971, 0.69146246, 0.84134475])
```

R DataFrames are automatically converted into Pandas DataFrames and vice versa.

```python
>>> gramex.ml.r('data(cars)')           # Load the cars dataset in R
>>> cars = gramex.ml.r('cars')          # Returns the dataset as a DataFrame
>>> cars.head()                         # To prove that, print it
   speed  dist
1    4.0   2.0
2    4.0  10.0
3    7.0   4.0
4    7.0  22.0
5    8.0  16.0
>>> type(cars)                          # Check the type
<class 'pandas.core.frame.DataFrame'>
```

It's OK to pass small data this way. Avoid converting large data though.
Instead, pass the *path* to the data. For example:

```python
gramex.ml.r('data <- read.csv(csv_file)', csv_file='../formhandler/flags.csv')
```

To get the location of the R script from within the R script, use the [here](https://www.rdocumentation.org/packages/here/versions/0.1) package:

```R
library(rprojroot)
# Loads data.csv from same directory as the R script
path = file.path(dirname(thisfile()), 'flags.csv')
flags = read.csv(path)
```

## R packages

Install packages in your R script as you would, normally. For example:

```R
packages <- c('randomForest', 'e1071', 'rpart', 'xgboost')
new.packages <- packages[!(packages %in% installed.packages()[,"Package"])]
if (length(new.packages)) install.packages(new.packages)

# Rest of your script can use the packages above.
library(randomForest)
# ... etc
```

This installs packages from [Microsoft CRAN](https://cran.microsoft.com/)
instead of prompting the user for a repository.

**Remember**: not all packages install both on Windows and Linux. Choose
packages with care.

## R plots

To render plots, save them into a temporary file. This script [plot.R](plot.R)
saves a plot to a temporary file and returns the path.

```R
library(grDevices)                                # This library saves to files
temp <- tempfile(fileext='.png')                  # Get a temporary PNG file name
png(file=temp, width=512, height=512)             # Save graphics to temp file
library(ggplot2)                                  # Use ggplot2 for graphics
plot(ggplot(norm) + aes_string(x='x', y='y') + geom_density2d())  # Draw the plot
dev.off()                                         # Stop saving to file
temp                                              # Return the temp file path
```

This code renders the plot:

```python
def plot(handler):
    path = gramex.ml.r(path='plot.R')
    return gramex.cache.open(path[0], 'bin')
```

[See the plot](plot.png).

## R async

[Run computations asynchronously](../functionhandler/#asynchronous-functions) if
they take time. This frees up Gramex to handle other requests.

To do this, you must:

- Decorate your FunctionHandler with `@tornado.gen.coroutine`
- Call `yield gramex.service.threadpool.submit(gramex.ml.r, **kwargs)` instead
  of `gramex.ml.r(**kwargs)`

For example, here the asynchronous version of the plotting code above:

```python
@tornado.gen.coroutine
def plot_async(handler):
    path = yield gramex.service.threadpool(gramex.ml.r, path='path/to/plot.R')
    raise tornado.gen.Return(gramex.cache.open(path[0], 'bin'))
```

![Asynchronous plot](plot_async.png)

## RMarkdown

Gramex renders RMarkdown files as HTML outputs using
[`FileHandler`](../filehandler/#transforming-content)
transform [`rmarkdown`](http://github.com/gramener/gramex/blob/master/gramex/transforms/rmarkdown.py).

Also saves the HTML file to the directory where `.Rmd` files are located.

Use below configuration to renders all `*.Rmd` files as HTML

```yaml
  r/rmarkdown:
    pattern: /$YAMLURL/(.*Rmd)
    handler: FileHandler
    kwargs:
      path: $YAMLPATH     # path at which Rmd files (.*Rmd) are located
      transform:
        "*.Rmd":          # Any file matching .Rmd
          function: rmarkdown(content, handler)
          headers:
            Content-Type: text/html
            Cache-Control: max-age=3600
```

<div class="example">
  <a class="example-demo" href="RMarkdown-story.Rmd" target="_blank">RMarkdown example</a>
  <a class="example-src" href="http://github.com/gramener/gramex/blob/master/gramex/apps/guide/r/RMarkdown-story.Rmd">Source</a>
</div>

<iframe class="w-100" src="RMarkdown-story.Rmd" style="height: 600px !important"></iframe>

To learn more about Rmarkdown, head over to
[RStudio's: Get started with Rmarkdown](https://rmarkdown.rstudio.com/lesson-1.html).
