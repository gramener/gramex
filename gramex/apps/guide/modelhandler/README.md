---
title: ModelHandler provides ML APIs
prefix: ModelHandler
...

ModelHandler exposes machine learning models as APIs that applications can use
via Python or over a REST API. (From **v1.35**.)

[TOC]

# Expose model

Gramex comes with a set of pre-trained models. These models can be exposed as
Python objects or as a REST API. For example, the [iris dataset][iris] has been
trained and is available as [iris.pkl](iris.pkl) in this directory. To use it in Python:

```python
import gramex.ml

model = gramex.ml.load('iris.pkl')
result = model.predict([{
  'sepal_length': 5.7,
  'sepal_width': 4.4,
  'petal_length': 1.5,
  'petal_width': 0.4,
}])
# result should be ['setosa']
```

This can be [exposed as a REST API](iris) using `ModelHandler`:

```yaml
url:
    modelhandler-iris:
        pattern: /$YAMLURL/iris
        handler: ModelHandler
        kwargs:
            path: $YAMLPATH/iris.pkl
```

- [Model info](iris) is available by calling the endpoint directly: `iris`
- [Prediction](iris?sepal_width=4.4&sepal_length=5.7&petal_length=1.5&petal_width=5)
  is available by passing all inputs: `iris?sepal_width=...&...`
- [Multiple predictions](iris?sepal_width=4.4&sepal_length=5.7&petal_length=1.5&petal_width=5&sepal_width=4.4&sepal_length=5.7&petal_length=1.5&petal_width=10)
  are available by repeating inputs: `iris?sepal_width=...&sepal_width=...&...`

[iris]: https://en.wikipedia.org/wiki/Iris_flower_data_set


# Train model

Gramex can train models with any dataset and save them. Gramex supports the
following types of models:

- [Classifier](#classifier): scikit-learn classifier models

## Classifier

To train a model, run:

```python
import pandas as pd
from gramex.ml import Classifier

# Read the data into a Pandas DataFrame
data = pd.read_csv('data.csv')
# Construct the model
model = Classifier()
model.train(
    data,                                 # DataFrame with input & output columns
    model_class='sklearn.svm.SVC',        # Any sklearn model works
    model_kwargs={'kernel': 'sigmoid'},   # Optional model parameters
    input=['var1', 'var2', 'var3'],       # Input column names in data
    output='output_column'                # Output column name in data
)
# Once the model is trained, save it
model.save('model.pkl')
```

This saves the model as a pickled object at `model.pkl`. This can be moved to
any location and [exposed via ModelHandler](#expose-model).

## GroupMeans

`gramex.ml` provides access to the `groupmeans()` function that allows you to see the most significant influencers of various metrics in your data. (**1.42**)

groupmeans accepts the following parameters- 

- `data` : pandas.DataFrame
- `groups` : non-empty iterable containing category column names in data
- `numbers` : non-empty iterable containing numeric column names in data
- `cutoff` : ignore anything with prob > cutoff. `cutoff=None` ignores significance checks, speeding it up a LOT.
- `quantile` : number that represents target improvement. Defaults to `.95`.
    - The `diff` returned is the % impact of everyone moving to the 95th percentile
- `minsize` : each group should contain at least `minsize` values.
    - If `minsize=None`, automatically set the minimum size to 1% of the dataset, or 10, whichever is larger.

For more information, see [autolysis.groupmeans](https://learn.gramener.com/docs/groupmeans.html.html)

For example, Groupmeans used in an FormHandler

```yaml
url:
  groupmeans-insights:
    pattern: /$YAMLURL/
    handler: FormHandler
    kwargs:
      url: $YAMPATH/yourdatafile.csv
      modify: groupmeans_app.groupmeans_insights(data, handler)

  groupmeans-data:
    pattern: /$YAMLURL/data
    handler: FormHandler
    kwargs:
      url: $YAMPATH/yourdatafile.csv
      default:
        _format: html
```

And in `groupmeans_app.py`

```python
import gramex.ml

def groupmeans_insights(data, handler):
    args = handler.argparse(
        groups={'nargs': '*', 'default': []},
        numbers={'nargs': '*', 'default': []},
        cutoff={'type': float, 'default': .01},
        quantile={'type': float, 'default': .95},
        minsize={'type': int, 'default': None},
        weight={'type': float, 'default': None})
    return gramex.ml.groupmeans(data, args.groups, args.numbers,
                                args.cutoff, args.quantile, args.weight)

```

# Links to Machine Learning and Analytics Usecases

[Groupmeans Applied to the National Acheivement Survey Dataset](../groupmeans/)