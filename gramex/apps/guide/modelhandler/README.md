---
title: ModelHandler provides ML APIs
prefix: ModelHandler
...

ModelHandler exposes machine learning models as APIs that applications can use
over a REST API. (From **v1.46**.)

[TOC]

# Expose Endpoints

Gramex allows for users to create models over an API interface.
To do so, add a modelhandler endpoint to the gramex app

```yaml
url:
  modelhandler:
    pattern: /$YAMLURL/model/(.*?)/(.*?)
    handler: ModelHandler
    kwargs:
      path: $YAMLPATH  # The local directory to store model files/training data etc.
```

Post this, users can create models by sending the appropriate requests to
the endpoint `/model/name/`,

- To create a model send a PUT/POST request to `/model/<name>/` with the following
URL Query Parameters or JSON Body Arguments
    - `model_class`: the scikit-learn class of the model you want to train
    - `url`: any valid formhandler URL, Currently, you can't send a file to the endpoint.
    If using a database, add a query/queryfunction/table as you would for formhandler.
    - `input`: the columns in the dataset to use as inputs for the model.
    - `output`: the output column.
    - `model_kwargs (optional)`: a dictionary with any model parameters
    - `labels (optional)`: list of possible output values
- creating a model, will not train by default - just create the model object and save it to disk.
- Send a PUT/POST Request with `Model-Retrain: true` in the request headers to train
the model on the training data.
- To get predictions, send a GET/POST Request to `/model/name/` with the input columns
as URL Query Parameters/JSON Body Arguments.
- Multiple predictions are available by sending lists through URL Query Parameters/JSON Body Arguments.
JSON Body Arguments can be formatted as follows

```JSON
{
    "col1":["val1","val2"],
    "col2":["val3","val4"],
    "model_class":"sklearn.ensemble.RandomForestClassifier"
}
```

URL Query Parameters can be sent as they usually are in formhandler -
`/model/<name>/?col1=val1&col2=val2&col1=val3..`

- You can view training data by sending a GET request to `/model/<name>/data`
and passing formhandler filters/extensions as URL query parameters
- You can edit/add to/Delete training data by sending the respective
PUT/POST/DELETE Request to `/model/<name>/data`
- Sending a DELETE Request to `/model/<name>/` will delete the model.

## Example Usage

for example, the following requests via [httpie](https://httpie.org/) will let you
create a model around the [iris dataset](https://en.wikipedia.org/wiki/Iris_flower_data_set)
assuming that the server has a iris.csv inside the app folder

```console
http PUT https://learn.gramener.com/guide/modelhandler/model/iris/ \
model_class=sklearn.linear_model.SGDClassifier \
output=species Model-Retrain:true url=iris.csv
```

If no input is sent, it will assume all columns except the output column are the input columns.

If no output is sent, it will assume the right-most or last column of the table is the output column.

Post which, visiting [this link](./model/iris/) wil return the model parameters and visiting
[this link](./model/iris/?sepal_width=4.4&sepal_length=5.7&petal_width=0.4&petal_length=1.5)
will return a prediction as a json object. (Answer should be setosa)

This form applies the URL query parameters directly. Try it.

<form action="./model/iris/">
  <p><label><input name="sepal_width" type="number" step="0.1" value="4.4"> Sepal Width</label></p>
  <p><label><input name="sepal_length" type="number" step="0.1" value="5.7"> Sepal Length</label></p>
  <p><label><input name="petal_width" type="number" step="0.1" value="0.4"> Petal Width</label></p>
  <p><label><input name="petal_length" type="number" step="0.1" value="1.5"> Petal Length</label></p>
  <button type="submit">Classify</button>
</form>

## API Reference

| Method | Endpoint | Input Format | Response/Action | Parameters | Header |
|--------|--------------------|----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|---------------------|
| GET | `/model/<name>/` | - | JSON, model kwargs |  |  |
| GET | `/model/<name>/data` | URL Query Parameter ?_format=json | Formhandler Format, training data |  |  |
| POST | `/model/<name>`| JSON Body {   "col1":"val1",   "col2":["val1",...] } URL Query Parameter ?model_class=...&input=...&input=... | Train a model (Model-Retrain in headers) else Get Prediction | model_class, input, output, url, labels, model_kwargs <column, value pairs> | Model-Retrain: true |
| POST | `/model/<name>/data` | JSON Body {   "col1":"val1",   "col2":["val1",...] } URL Query Parameter ?id=...&col1=... | Inserts rows into training data |  <column, value pairs> |  |
| PUT | `/model/<name>/` | JSON Body {   "col1":"val1",    "col2":["val1",...] } URL Query Parameter ?model_class=...&input=...&input=... | Train a model | model_class, input, output, url, labels, model_kwargs <column, value pairs> | Model-Retrain: true |
| PUT | `/model/<name>/data` | JSON Body {   "col1":"val1",   "col2":["val1",...] } URL Query Parameter ?id=...&col1=... | Filters rows by columns in id and updates with rest of args | id, <column, value pairs> |  |
| DELETE | `/model/<name>` |  | Delete a model |  |  |
| DELETE | `/model/<name>/data` | JSON Body {   "id": } URL Query Parameter ?id=...&col1=... | Delete rows based on id, id needs to be a primary or composite key and in the case of files, a string/object type column   |  |  |

# Classifier

To train a machine learning model in python, run:

```python
import pandas as pd
from gramex.ml import Classifier

# Read the data into a Pandas DataFrame
data = pd.read_csv('data.csv')
# Construct the model
model = Classifier(
  model_class='sklearn.svm.SVC',        # Any sklearn model works
  model_kwargs={'kernel': 'sigmoid'},   # Optional model parameters
  input=['var1', 'var2', 'var3'],       # Input column names in data
  output='output_column'                # Output column name in data
)
model.train(data)                       # data is any pandas dataframe
model.save('model.pkl')                 # Once the model is trained, save it
```

and to make predictions in python, 

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

# GroupMeans

`gramex.ml` provides access to the `groupmeans()` function that allows you to see
the most significant influencers of various metrics in your data. (**1.42**)

groupmeans accepts the following parameters- 

- `data` : pandas.DataFrame
- `groups` : non-empty iterable containing category column names in data
- `numbers` : non-empty iterable containing numeric column names in data
- `cutoff` : ignore anything with prob > cutoff. `cutoff=None` ignores significance checks,
speeding it up a LOT.
- `quantile` : number that represents target improvement. Defaults to `.95`.
    - The `diff` returned is the % impact of everyone moving to the 95th percentile
- `minsize` : each group should contain at least `minsize` values.
    - If `minsize=None`, automatically set the minimum size to 1% of the dataset,
    or 10, whichever is larger.

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