import json
import yaml
import gramex
from . import TestGramex

class TestIde(TestGramex):
    def test_get(self):
        url = '/ide_config_handler?filename=test_ide.yaml'
        file_text = gramex.cache.open('test_ide.json')
        json_obj = {k: v for d in file_text for k, v in d.items()}
        result = self.get(url).content
        self.assertEquals(json_obj['body_data'], json.loads(result.decode("utf-8")))

    def test_post(self):
        url = '/ide_config_handler?filename=test_ide.yaml'
        file_text = gramex.cache.open('test_ide.json')
        json_obj = {k: v for d in file_text for k, v in d.items()}
        result = self.check(url, method='post', data=json.dumps(json_obj['body_data']))
        self.assertEquals(result.text, '{"Result": [{"Success": "true"}]}')
        data = gramex.cache.open('test_ide.yaml')
        self.assertEquals(data, json_obj['text'])
