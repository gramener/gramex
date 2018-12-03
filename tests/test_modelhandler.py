import os
import json
import pandas as pd
from shutil import copyfile
from nose.tools import eq_, ok_
from . import folder, TestGramex


class TestModelHandler(TestGramex):
    @classmethod
    def setUpClass(cls):
        # Create a model and copy iris.csv to the tests/ folder
        original_iris_path = os.path.join(folder, '..', 'testlib', 'iris.csv')
        copyfile(original_iris_path, os.path.join(folder, 'iris.csv'))

    @classmethod
    def tearDownClass(cls):
        for file_ in {'iris.csv', 'iris.pkl', 'iris2.pkl'}:
            if os.path.exists(os.path.join(folder, file_)):
                os.unlink(os.path.join(folder, file_))

    def test_model_info(self):
        # PUT should return 200
        self.check(url='/model/iris2/', method='put')
        r = self.check('/model/iris2/', method='get')
        info = r.json()  # Get Model Info
        ok_('BernoulliNB' in info['model_class'])
        eq_(info['trained'], False)

    def test_train_model_check_info(self):
        self.check('/model/iris/', method='put',
                   data=json.dumps({'url': 'iris.csv',
                                    'model_class': 'sklearn.linear_model.SGDClassifier'}),
                   request_headers={'Model-Retrain': 'True'})
        r = self.check('/model/iris/')
        info = r.json()
        eq_(info['trained'], True)
        eq_(info['input'], ['sepal_length',
                            'sepal_width', 'petal_length', 'petal_width'])
        eq_(info['output'], 'species')

    def test_predict(self):
        data = [
            {'sepal_length': 5, 'sepal_width': 3, 'petal_length': 1.5, 'petal_width': 0},
            {'sepal_length': 5, 'sepal_width': 2, 'petal_length': 5.0, 'petal_width': 1},
            {'sepal_length': 6, 'sepal_width': 3, 'petal_length': 4.8, 'petal_width': 2},
        ]
        # Test individual results
        self.check('/model/iris/', method='put',
                   data=json.dumps({'url': 'iris.csv',
                                    'model_class': 'sklearn.linear_model.SGDClassifier'}),
                   request_headers={'Model-Retrain': 'True'})
        # In case model not trained, train it.
        single = [
            self.check('/model/iris/', method='post', data=json.dumps(k))
            for k in data
        ]
        single_responses = [response.json()[0] for response in single]
        ok_(all(response['result'] in {'setosa', 'versicolor', 'virginica'}
                for response in single_responses))
        data_df = pd.DataFrame(data)
        # Test multiple results
        multi = self.check('/model/iris/', method='post',
                           data=json.dumps(data_df.to_dict(orient='list')))
        eq_(multi.json(), single_responses)
        # eq_([result['result'] for result in multi.json()], ['setosa', 'versicolor', 'virginica'])
        # This currently does not work since the model is not deterministic

    def test_predict_incomplete(self):
        self.check('/model/iris/', method='post',
                   data=json.dumps({'sepal_length': 5}), code=500)

    def test_change_params_without_training(self):
        self.check('/model/iris/', method='put',
                   data=json.dumps({'url': 'iris.csv',
                                    'model_class': 'sklearn.linear_model.SGDClassifier'}),
                   request_headers={'Model-Retrain': 'True'})
        # Train a model
        self.check('/model/iris/', method='post',
                   data=json.dumps({'model_class': 'sklearn.ensemble.RandomForestClassifier'}))
        # Change a parameter
        r = self.check('/model/iris/').json()
        eq_(r['model_class'], 'sklearn.ensemble.RandomForestClassifier')
        eq_(r['trained'], False)

    def test_delete_model(self):
        self.check('/model/iris/', method='delete')
        ok_('iris.pkl' not in os.listdir(folder))

    def test_get_training_data(self):
        self.check('/model/iris/', method='put',
                   data=json.dumps({'url': 'iris.csv'}),
                   request_headers={'Model-Retrain': 'True'})
        r = self.check('/model/iris/data?').json()
        training_file = pd.read_csv(os.path.join(folder, 'iris.csv'), encoding='utf-8')
        eq_(len(r), len(training_file))

    # def test_add_training_data(self):
        # Gets interpreted as string which breaks other tests
        # TODO: Fix Data.py update and insert types then re-add this test
        # self.check('/model/iris/', method='put',
        #            data=json.dumps({'url': 'iris.csv'}),
        #            request_headers={'Model-Retrain': 'True'})
        # self.check('/model/iris/data', data=json.dumps({'sepal_width': 10,
        #                                                 'sepal_length': 10,
        #                                                 'petal_length': 10,
        #                                                 'petal_width': 10,
        #                                                 'specis':'test_insert'}),
        #                                                 method='post')

    # def test_remove_training_data(self):
    #     ...

    # def test_update_training_data(self):
    #     ...
