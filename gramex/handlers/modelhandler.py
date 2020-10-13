import os
import json
import gramex.ml
import pandas as pd
import gramex.cache
import gramex.data
from gramex.handlers import BaseHandler
import tornado.escape
from io import BytesIO

_model_cache = {}


class ModelHandler(BaseHandler):
    '''
    Allows users to create API endpoints to train/test models exposed through Scikit-Learn.
    TODO: support Scikit-Learn Pipelines for data transformations.
    '''
    def _load_keras_model(self, path):
        """Load a Keras model into a local cache.

        Parameters
        ----------
        path : str
            Path to a Keras model.
        """
        model = _model_cache.get(path, False)
        if not model:
            _model_cache[path] = gramex.cache.open(path)
        return _model_cache[path]

    @classmethod
    def setup(cls, path, **kwargs):
        if os.path.splitext(path)[-1] == '.h5':
            from tensorflow.keras.models import load_model
            gramex.cache.open_callback['h5'] = load_model
            cls.model_type = "keras"
            cls._model_loader = cls._load_keras_model
        else:
            cls.model_type = "sklearn"
            cls._model_loader = staticmethod(lambda x: gramex.cache.open(x, gramex.ml.load))
        super(ModelHandler, cls).setup(**kwargs)
        prepare = kwargs.get('prepare', False)
        if prepare:
            from pydoc import locate
            cls.prepare = locate(prepare)
        cls.path = path

    def prepare(self):
        '''
        Gets called automatically at the beginning of every request.
        takes model name from request path and creates the pickle file path.
        Also merges the request body and the url query args.
        url query args have precedence over request body in case both exist.
        Expects multi-row paramets to be formatted as the output of handler.argparse.
        '''
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        if self.model_type == "sklearn":
            self.model_path = os.path.join(
                self.path, self.path_args[0] + '.pkl')
            self.request_body = {}
            if self.request.body:
                self.request_body = tornado.escape.json_decode(self.request.body)
        elif self.model_type == "keras":
            self.model_path = self.path
            from skimage.io import imread
            self.request_body = {'image': imread(BytesIO(self.request.body))}
        if self.args:
            self.request_body.update(self.args)
        url = self.request_body.get('url', '')
        if url and gramex.data.get_engine(url) == 'file':
            self.request_body['url'] = os.path.join(self.path, os.path.split(url)[-1])

    def get_data_flag(self):
        '''
        Return a True if the request is made to /model/name/data.
        '''
        if len(self.path_args) > 1 and self.path_args[1] == 'data':
            return True

    def get(self, *path_args):
        '''
        Request sent to model/name with no args returns model information,
        (that can be changed via PUT/POST).
        Request to model/name with args will accept model input and produce predictions.
        Request to model/name/data will return the training data specified in model.url,
        this should accept most formhandler flags and filters as well.
        '''
        model = self._model_loader(self.model_path)
        if self.get_data_flag():
            file_kwargs = self.listify(['engine', 'url', 'ext', 'table', 'query', 'id'])
            _format = file_kwargs.pop('_format', ['json'])[0]
            # TODO: Add Support for formhandler filters/limit/sorting/groupby
            data = gramex.data.filter(model.url, **file_kwargs)
            self.write(gramex.data.download(data, format=_format, **file_kwargs))
            return
        # If no model columns are passed, return model info
        if not vars(model).get('input', '') or not any(col in self.args for col in model.input):
            model_info = {k: v for k, v in vars(model).items()
                          if k not in ('model', 'scaler')}
            self.write(json.dumps(model_info, indent=4))
            return
        self._predict(model)

    def put(self, *path_args, **path_kwargs):
        '''
        Request to /model/name/ with no params will create a blank model.
        Request to /model/name/ with args will interpret as model paramters.
        Set Model-Retrain: true in headers to either train a model from scratch or extend it.
        To Extend a trained model, don't update the parameters and send Model-Retrain in headers.
        Request to /model/name/data with args will update the training data,
        doesn't currently work on DF's thanks to the gramex.data bug.
        '''
        try:
            model = self._model_loader(self.model_path)
        except EnvironmentError: # noqa
            model = gramex.ml.Classifier(**self.request_body)
        if self.get_data_flag():
            file_kwargs = self.listify(model.input + [model.output] + ['id'])
            gramex.data.update(model.url, args=file_kwargs, id=file_kwargs['id'])
        else:
            if not self._train(model):
                model.save(self.model_path)

    def _predict(self, model):
        '''Helper function for model.train.'''
        if self.model_type == "sklearn":
            params = self.listify(model.input)
            if hasattr(model, 'model') and model.trained:
                data = pd.DataFrame(params)
                data = data[model.input]
                data['result'] = model.predict(data)
                self.write(data.to_json(orient='records'))
            elif params:
                raise AttributeError('model not trained')
            else:
                return
        elif self.model_type == "keras":
            from skimage.transform import resize
            image = self.request_body['image']
            height, width = model.input.shape[1:-1]
            image = resize(image, (height, width))
            pred = model.predict(image.reshape((1,) + image.shape)).ravel()
            self.write(json.dumps(pred.tolist()))

    def post(self, *path_args, **path_kwargs):
        '''
        Request to /model/name/ with Model-Retrain: true in the headers will,
        attempt to update model parameters and retrain/extend the model.
        Request to /model/name/ with model input as body/query args and no Model-Retrain,
        in headers will return predictions.
        Request to /model/name/data lets people add rows the test data.
        '''
        # load model object - if it doesn't exist, send a response asking to create the model
        try:
            model = self._model_loader(self.model_path)
        except EnvironmentError: # noqa
            # Log error
            self.write({'Error': 'Please Send PUT Request, model does not exist'})
            raise EnvironmentError # noqa
        if self.get_data_flag():
            file_kwargs = self.listify(model.input + [model.output])
            gramex.data.insert(model.url, args=file_kwargs)
        else:
            # If /data/ is not path_args[1] then post is sending a predict request
            # Keras models cannot yet be trained by ModelHandler
            if self.model_type == "sklearn" and self._train(model):
                return
            self._predict(model)

    def delete(self, *path_args):
        '''
        Request to /model/name/ will delete the trained model.
        Request to /model/name/data needs id and will delete rows from the training data.
        '''
        if self.get_data_flag():
            file_kwargs = self.listify(['id'])
            try:
                model = self._model_loader(self.model_path)
            except EnvironmentError: # noqa
                self.write(
                    {'Error': 'Please Send PUT Request, model does not exist'})
                raise EnvironmentError # noqa
            gramex.data.delete(model.url, args=file_kwargs, id=file_kwargs['id'])
            return
        if os.path.exists(self.model_path):
            os.unlink(self.model_path)

    def _train(self, model):
        ''' Looks for Model-Retrain in Request Headers,
        trains a model and pickles it.
        '''
        # Update model parameters
        model.update_params(self.request_body)
        if 'Model-Retrain' in self.request.headers:
            # Pass non model kwargs to gramex.data.filter
            try:
                data = gramex.data.filter(
                    model.url,
                    args=self.listify(['engine', 'url', 'ext', 'table', 'query', 'id']))
            except AttributeError:
                raise AttributeError('Model does not have a url')
            # Train the model.
            model.train(data)
            model.trained = True
            model.save(self.model_path)
            return True

    def listify(self, checklst):
        ''' Some functions in data.py expect list values, so creates them.
        checklst is list-like which contains the selected values to be returned.
        '''
        return {
            k: [v] if not isinstance(v, list) else v
            for k, v in self.request_body.items()
            if k in checklst
        }
