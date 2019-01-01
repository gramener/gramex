import os
import gramex.ml
from gramex.config import variables
from nose.tools import eq_
from testlib.test_ml import translate_mock, _translate_count
from . import TestGramex


class TestTranslater(TestGramex):
    @classmethod
    def setUpClass(cls):
        cls.stores = ['db', 'xlsx']
        cls.caches = [
            variables['TRANSLATE_' + store.upper()]
            for store in cls.stores
        ]
        cls.tearDownClass()
        gramex.ml.translate_api['mock'] = translate_mock

    def test_translate(self):
        for store in self.stores:
            url = '/translate/' + store
            r = self.check(url, data={'q': 'Apple'}).json()
            eq_(r, [{'q': 'Apple', 't': 'appel', 'source': 'en', 'target': 'nl'}])
            r = self.check(url, data={'q': ['Apple', 'Orange']}).json()
            eq_(r, [
                {'q': 'Apple', 't': 'appel', 'source': 'en', 'target': 'nl'},
                {'q': 'Orange', 't': 'Oranje', 'source': 'en', 'target': 'nl'}
            ])
            count = len(_translate_count)
            r = self.check(url, data={'q': ['Apple', 'Orange'], 'target': 'de'}).json()
            eq_(r, [
                {'q': 'Apple', 't': 'Apfel', 'source': 'en', 'target': 'de'},
                {'q': 'Orange', 't': 'Orange', 'source': 'en', 'target': 'de'}
            ])
            eq_(len(_translate_count), count + 1)
            # Ensure that cache does not trigger request again
            r = self.check(url, data={'q': ['Apple', 'Orange'], 'target': 'de'}).json()
            eq_(len(_translate_count), count + 1)

    @classmethod
    def tearDownClass(cls):
        for path in cls.caches:
            if os.path.exists(path):
                os.remove(path)
