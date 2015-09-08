import yaml
import unittest
from pathlib import Path
from config import LayeredConfig
from orderedattrdict import AttrDict


class TestLayeredConfig(unittest.TestCase):
    'Test LayeredConfig'

    def setUp(self):
        self.conf = LayeredConfig('a', 'b')
        self.home = Path(__file__).absolute().parent
        self.paths = LayeredConfig(
            ('a', self.home / 'config.a.yaml'),
            ('b', self.home / 'config.b.yaml'))
        # config.a.yaml links to config.c.yaml. It mist be missing initially
        self.newconfig = self.home / 'config.c.yaml'
        if self.newconfig.exists():
            self.newconfig.unlink()
        self.final = LayeredConfig(('final', self.home/'config.final.yaml'))

    def test_add_layer(self):
        conf = LayeredConfig()
        conf += 'a'
        conf += ('b', self.home/'config.b.yaml')
        conf.a.x = conf.b.y = 1
        with self.assertRaises(AttributeError):
            conf.c.x = 1

    def test_override(self):
        'Identical keys override prior layers'
        self.conf.a.x = 1
        self.conf.b.x = 2
        self.assertEqual(+self.conf, {'x': 2})

        self.conf.a.y = 3
        self.conf.b.y = 4
        self.assertEqual(+self.conf, {'x': 2, 'y': 4})

    def test_inheritence(self):
        'Different keys overlay on prior layers'
        self.conf.a.x = 1
        self.conf.b.y = 2
        self.assertEqual(+self.conf, {'x': 1, 'y': 2})

    def test_clear_none(self):
        'None values act as blocks, clearing the key'
        self.conf.a.x = 1
        self.conf.b.x = None
        self.assertEqual(+self.conf, {})

        del self.conf.b.x
        self.assertEqual(+self.conf, {'x': 1})

    def test_load(self):
        'Config files are loaded and merged'
        self.assertEqual(+self.paths, +self.final)

    def test_update(self):
        'Config files are updated on change'
        data = AttrDict(a=1, b=2)
        conf = LayeredConfig(('c', self.newconfig))

        # When the file is missing, it is blank
        if self.newconfig.exists():
            self.newconfig.unlink()
        self.assertEqual(+conf, {})

        # Once created, it is automatically reloaded
        with self.newconfig.open('w') as out:
            yaml.dump(data, out)
        self.assertEqual(+conf, data)

        # Remove the file finally
        self.newconfig.unlink()
