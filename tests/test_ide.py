import json
import yaml
from . import TestGramex


class TestIde(TestGramex):
    def test_get(self):
        url = '/ide_config_handler?filename=test_ide.yaml'
        result = self.get(url).content
        with open('test_ide.json', 'r') as fin:
            text = json.load(fin)
        self.maxDiff = None
        self.assertEquals(text, json.loads(result.decode("utf-8")))

    def test_post(self):
        url = '/ide_config_handler?filename=test_ide1.yaml'
        with open('test_ide.json', 'r') as fin:
            body_text = json.load(fin)

        text = json.loads('{"url": {"Key": "Value", "Key1": "Value", "template": {"handler": "FileHandler", "kwargs": ' \
                    '{"path": "templates/", "template": "*"}, "pattern": "/templates/(.*)"}}}')

        result = self.check(url, method='post', data=json.dumps(body_text))
        if result.text == '{"Result": [{"Success": "true"}]}':
            with open('test_ide1.yaml', 'r') as fin:
                data = yaml.safe_load(fin)
                self.maxDiff = None
                self.assertEquals(data, text)
