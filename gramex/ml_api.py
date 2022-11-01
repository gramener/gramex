from abc import ABC, abstractmethod
from inspect import signature, _empty
import os.path as op
import re
from typing import Any, Optional, Union, List
import warnings

from gramex import cache
from gramex.config import locate, app_log
from gramex.install import _mkdir
import joblib
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TRANSFORMS = {
    "include": [],
    "exclude": [],
    "dropna": True,
    "drop_duplicates": True,
    "pipeline": True,
    "nums": [],
    "cats": [],
    "target_col": None,
    "index_col": None,
}
SEARCH_MODULES = {
    "gramex.ml_api.SklearnModel": [
        "sklearn.linear_model",
        "sklearn.tree",
        "sklearn.ensemble",
        "sklearn.svm",
        "sklearn.neighbors",
        "sklearn.neural_network",
        "sklearn.naive_bayes",
    ],
    "gramex.ml_api.SklearnTransformer": [
        "sklearn.decomposition",
        "gramex.ml",
    ],
    "gramex.sm_api.StatsModel": [
        "statsmodels.tsa.api",
        "statsmodels.tsa.statespace.sarimax",
    ],
    "gramex.ml_api.HFTransformer": ["gramex.transformers"],
}


def search_modelclass(mclass: str) -> Any:
    """Search for an ML algorithm or estimator by its name within supported modules.

    Each estimator also comes with a wrapper class through which MLHandler can use it.
    Wrapper classes are:
    1. SklearnModel (for subclasses of sklearn.base.{ClassifierMixin, RegressorMixin})
    2. SklearnTransformer (for subclasses of sklearn.base.TransformerMixin)
    3. StatsModel (for statsmodels)

    Parameters
    ----------
    mclass : str
        Name of a model / estimator / algorithm

    Returns
    -------
    tuple of class, wrapper

    Raises
    ------
    ImportError
        If the required class is not found anywhere in the supported modules.

    Example
    -------
    >>> klass, wrapper = search_modelclass('LogisticRegression')
    >>> print(klass)
    <class 'sklearn.linear_model._logistic.LogisticRegression'>
    >>> print(wrapper)
    <class 'gramex.ml_api.SklearnModel'>
    """
    for wrapper, modules in SEARCH_MODULES.items():
        klass = locate(mclass, modules)
        if klass:
            return klass, wrapper
    raise ImportError(f"{mclass} not found.")


def coerce_model_params(mclass: str, params: dict) -> dict:
    """Coerce a dictionary of parameters into the types expected by a given class constructor.

    This is typically used when hyperparamters are set through HTTP request bodies.

    Parameters
    ----------
    mclass : str
        Name of a model / estimator / algorithm
    params : dict
        A dictionary containing named parameters and their values used to instantiate `mlclass`.

    Returns
    -------
    dict
        A copy of `params`, with values typecasted into the types expected by `mlclass`.

    Example
    -------
    >>> params = {"C": "1.0", max_iter: "100"}  # Values are strings
    >>> coerce_model_params('LogisticRegression', params)
    {"C": 1.0, max_iter: 100}  # Values are numbers
    """
    if not params:
        return {}
    model, _ = search_modelclass(mclass)
    validated = {}
    sig_params = signature(model).parameters
    for param in sig_params & params.keys():
        val = params.pop(param)
        _sig_p = sig_params[param]
        annotation = _sig_p.annotation
        val = annotation(val) if annotation is not _empty else type(_sig_p.default)(val)
        validated[param] = val
    return validated


def assemble_pipeline(
    data: pd.DataFrame,
    target_col: str,
    model: Union[BaseEstimator, str],
    nums: Optional[str] = None,
    cats: Optional[str] = None,
    **kwargs,
) -> Pipeline:
    """Create an sklearn pipeline to preprocess features.

    Parameters
    ----------
    data : pd.DataFrame
        The training data.
    target_col : str
        The column name of the target, must be present in `data`.
    model : sklearn.base.BaseEstimator
        The sklearn estimator which is fitted at the end of the pipeline, after the preprocessing.
    nums : list
        Numerical columns in `data`, to be StandardScaled with the pipeline.
    cats : list
        Categorical columns in `data`, to be OneHotEncoded with the pipeline.
    kwargs : Additional parameters for the model constructor.

    Returns
    -------
    sklearn.pipeline.Pipleline
        An sklearn pipeline containing two steps.
        1. A `sklearn.compose.ColumnTransformer` step that one-hot encodes categorical variables,
           and StandardScales numerical ones.
        2. An estimator

    Example
    -------
    >>> df = pd.read_csv('superstore-sales.csv', usecols=['region', 'discount', 'profit'])
    >>> assemble_pipeline(df, 'profit', 'LogisticRegression', nums=['discount'], cats=['region'])
    Pipeline(steps=[('transform',
                    ColumnTransformer(transformers=[('ohe',
                                                     OneHotEncoder(sparse=False),
                                                     ['region']),
                                                    ('scaler', StandardScaler(),
                                                     ['discount'])])),
                    ('LogisticRegression', LogisticRegression())])
    """
    if isinstance(model, str):
        model, _ = search_modelclass(model)(**kwargs)
    nums = set(nums) - {target_col} if nums else set()
    cats = set(cats) - {target_col} if cats else set()
    both = nums & cats
    if len(both) > 0:
        raise ValueError(f"Columns {both} cannot be both numerical and categorical.")
    to_guess = set(data.columns.tolist()) - nums.union(cats) - {target_col}
    numericals = list(nums)
    categoricals = list(cats)
    for c in to_guess:
        if pd.api.types.is_numeric_dtype(data[c]):
            numericals.append(c)
        else:
            categoricals.append(c)

    ct = ColumnTransformer(
        [
            ("ohe", OneHotEncoder(sparse=False), categoricals),
            ("scaler", StandardScaler(), numericals),
        ]
    )
    return Pipeline([("transform", ct), (model.__class__.__name__, model)])


class ModelStore(cache.JSONStore):
    """A hybrid version of keystore that stores models, data and parameters."""

    def __init__(self, path, *args, **kwargs):
        _mkdir(path)
        self.data_store = op.join(path, "data.h5")
        self.model_path = op.join(path, "model.pkl")
        self.path = path
        super(ModelStore, self).__init__(op.join(path, "config.json"), *args, **kwargs)

    def model_kwargs(self):
        return {k: self.load(k) for k in TRANSFORMS}

    def load(self, key, default=None):
        if key in ("transform", "model"):
            return super(ModelStore, self).load(key, {})
        return self.load("transform").get(
            key,
            TRANSFORMS.get(key, self.load("model").get(key, default)),
        )

    def dump(self, key, value):
        if key in TRANSFORMS:
            transform = super(ModelStore, self).load("transform", {})
            transform[key] = value
            super(ModelStore, self).dump("transform", transform)
        elif key in ("class", "params"):
            model = super(ModelStore, self).load("model", {})
            model[key] = value
            if key == "class":
                warnings.warn("Model changed, removing old parameters.")
                model["params"] = {}
            super(ModelStore, self).dump("model", model)
        self.flush()

    def load_data(self, default=pd.DataFrame()):
        try:
            df = cache.open(self.data_store, key="data")
        except (KeyError, FileNotFoundError):
            df = default
        return df

    def store_data(self, df, append=False, **kwargs):
        df.to_hdf(self.data_store, format="table", key="data", append=append, **kwargs)
        return self.load_data(df)


class AbstractModel(ABC):
    """Abstract base class for all models supported by MLHandler.
    MLHandler will assume ONLY this interface.
    """

    @abstractmethod
    def fit(self, *args, **kwargs) -> Any:
        """Fit the model.

        Ensure that all variations like partial_fit, or fit called without a target, etc,
        are sufficiently handled by the concrete implementations.
        """

    @abstractmethod
    def predict(self, *args, **kwargs) -> pd.Series:
        """Get a prediction as a pandas Series."""

    @abstractmethod
    def get_params(self, *args, **kwargs) -> dict:
        """Get the (hyper)parameters  of the model."""

    @abstractmethod
    def score(self, *args, **kwargs) -> float:
        """Score the model against some y_true."""

    @abstractmethod
    def get_attributes(self, *args, **kwargs) -> dict:
        """Get the _learned_ attributes of the model."""


class SklearnModel(AbstractModel):
    """SklearnModel."""

    @classmethod
    def from_disk(cls, path, **kwargs):
        model = cache.open(path, joblib.load)
        if isinstance(model, Pipeline):
            _, wrapper = search_modelclass(model[-1].__class__.__name__)
        else:
            _, wrapper = search_modelclass(model.__class__.__name__)
        return cls(model, params={})

    def __init__(
        self,
        model: Any,
        data: Optional[pd.DataFrame] = None,
        target_col: Optional[str] = None,
        nums: Optional[List[str]] = None,
        cats: Optional[List[str]] = None,
        params: Any = None,
        **kwargs,
    ):
        if not isinstance(model, Pipeline) and any([nums, cats]):
            self.model = assemble_pipeline(data, target_col, model, nums, cats, **kwargs)
        else:
            self.model = model
        self.kwargs = kwargs

    def _fit(self, X, y):
        if hasattr(self.model, "partial_fit"):
            return self.model.partial_fit(X, y, classes=np.unique(y))
        return self.model.fit(X, y)

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        model_path: str = "",
        name: str = "",
        **kwargs,
    ):
        """Fit the model.

        Parameters
        ----------
        X : array-like
            Training features.
        y : array-like
            Training labels
        model_path : str, optional
            If specified, the model is saved at this path.
        name : str, optional
            Name of the handler instance calling this method.
        kwargs : Additional parameters for `model.fit`
        """
        app_log.info("Starting training...")
        try:
            result = self._fit(X, y)
            app_log.info("Done training...")
        except Exception as exc:
            app_log.exception(exc)
            return self.model
        if model_path:
            joblib.dump(self.model, model_path)
            app_log.info(f"{name}: Model saved at {model_path}.")
        return result

    def _predict(self, X, **kwargs):
        try:
            y = self.model.predict(X, **kwargs)
        except RuntimeError:
            y = self.model.predict(X[self.model["transform"]._feature_names_in], **kwargs)
        return y

    def predict(self, X: Union[pd.DataFrame, np.ndarray], target_col: str = "", **kwargs):
        """Get a prediction.

        Parameters
        ----------
        X : array-like
            Input features
        target_col : str, optional
            If specified, predictions are added as a column to `X`, with this as the column name.
        kwargs : Additionnal parameters for `model.predict`
        """
        p = self._predict(X, **kwargs)
        if target_col:
            try:
                X[target_col] = p
            except ValueError:
                # This happens for NER: predictions of a single sample can be multiple entities.
                X[target_col] = [p]
            return X
        return p

    def get_params(self, **kwargs):
        # self.model could be a pipeline or a raw sklearn estimator
        model = self.model[-1] if isinstance(self.model, Pipeline) else self.model
        return model.get_params(**kwargs)

    def score(self, X, y_true, **kwargs):
        return self.model.score(X, y_true, **kwargs)

    def get_attributes(self):
        if isinstance(self.model, Pipeline):
            model = self.model[-1]
        else:
            model = self.model
        return {k: v for k, v in vars(model).items() if re.search(r"[^_]+_$", k)}


class SklearnTransformer(SklearnModel):
    """SklearnTransformer."""

    def _predict(self, X, **kwargs):
        """Sklearn transformers don't have a "predict", they have a "transform"."""
        return self.model.transform(X, **kwargs)


class HFTransformer(SklearnModel):
    def __init__(self, model, params=None, data=None, **kwargs):
        self.model = model
        if params is None:
            params = {"text_col": "text", "target_col": "label"}
        self.params = params
        self.kwargs = kwargs

    @classmethod
    def from_disk(cls, path, klass):
        model = op.join(path, "model")
        tokenizer = op.join(path, "tokenizer")
        return cls(klass(model, tokenizer))

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        model_path: str = "",
        name: str = "",
        **kwargs,
    ):
        text = X.squeeze("columns")
        self.model.fit(text, y, model_path, **kwargs)

    def _predict(self, X: Union[pd.DataFrame, np.ndarray], target_col: str = "", **kwargs):
        text = X["text"]
        return self.model.predict(text)
