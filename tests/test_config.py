import yaml
import unittest
from pathlib import Path
from gramex.config import ChainConfig, PathConfig
from orderedattrdict import AttrDict


def unlink(path):
    if path.exists():
        path.unlink()


class TestChainConfig(unittest.TestCase):
    'Test gramex.conf.ChainConfig'

    def test_attrdict(self):
        'ChainConfig is an AttrDict'
        conf = ChainConfig(a=AttrDict(), b=AttrDict())
        conf.a.x = 1
        conf.a.y = 2
        self.assertEqual(conf, {'a': {'x': 1, 'y': 2}, 'b': {}})
        conf.b.x = 3
        conf.b.y = 4
        self.assertEqual(conf, {'a': {'x': 1, 'y': 2}, 'b': {'x': 3, 'y': 4}})

    def test_overlay(self):
        '+ChainConfig updates configs successively'
        conf = ChainConfig(a=AttrDict(), b=AttrDict())
        conf.a.x = 1
        conf.a.y = 2
        conf.b.x = 2
        self.assertEqual(+conf, {'x': 2, 'y': 2})
        conf.b.x = None
        self.assertEqual(+conf, {'y': 2})


class TestPathConfig(unittest.TestCase):
    'Test gramex.conf.PathConfig'

    def setUp(self):
        self.home = Path(__file__).absolute().parent
        self.a = self.home / 'config.a.yaml'
        self.b = self.home / 'config.b.yaml'
        self.c = self.home / 'config.c.yaml'
        self.final = self.home / 'config.final.yaml'

    def test_merge(self):
        'Config files are loaded and merged'
        unlink(self.c)
        conf = ChainConfig([
            ('a', PathConfig(self.a)),
            ('b', PathConfig(self.b))])
        self.assertEqual(+conf, PathConfig(self.final))

    def test_update(self):
        'Config files are updated on change'
        conf = ChainConfig(c=PathConfig(self.c))

        # When the file is missing, config is empty
        unlink(self.c)
        self.assertEqual(+conf, {})

        # When the file is blank, config is empty
        with self.c.open('w') as out:
            out.write(u'')
        self.assertEqual(+conf, {})

        # Once created, it is automatically reloaded
        data = AttrDict(a=1, b=2)
        with self.c.open('w') as out:
            yaml.dump(data, out)
        self.assertEqual(+conf, data)

        # Deleted file is detected
        self.c.unlink()
        self.assertEqual(+conf, {})
