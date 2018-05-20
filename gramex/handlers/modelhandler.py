import json
import pandas as pd
import gramex.ml
import gramex.cache
from gramex.handlers import BaseHandler


class ModelHandler(BaseHandler):
    '''
    TODO
    '''
    @classmethod
    def setup(cls, path, **kwargs):
        super(ModelHandler, cls).setup(**kwargs)
        cls.path = path

    def get(self):
        model = gramex.cache.open(self.path, gramex.ml.load)
        self.set_header('Content-Type', 'application/json; charset=utf-8')

        # If no model columns are passed, return model info
        if not any(col in self.args for col in model.input):
            self.write(json.dumps({
                'model': repr(model.model),
                'input': model.input,
                'output': model.output,
            }, indent=4))
            return

        data = pd.DataFrame(self.args)
        data = data[model.input]
        data = model.scaler.transform(data)
        result = model.predict(data).tolist()
        result = {'result': result}
        self.write(result)
