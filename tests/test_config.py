import os
import six
import yaml
import unittest
from pathlib import Path
from gramex.config import ChainConfig, PathConfig, walk, merge
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader

info = AttrDict(
    home=Path(__file__).absolute().parent,
)


def setUpModule():
    # Ensure that we're running gramex from the parent of this tests/ directory.
    # The configurations (config.template.*yaml) are based on this assumption.
    info.cwd = os.getcwd()
    os.chdir(str(info.home.parent))


def tearDownModule():
    os.chdir(info.cwd)


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
        conf = ChainConfig()
        conf.a = AttrDict()
        conf.b = AttrDict()
        conf.a.x = 1
        conf.a.y = 2
        conf.b.x = 2
        self.assertEqual(+conf, {'x': 2, 'y': 2})
        conf.b.x = None
        self.assertEqual(+conf, {'y': 2})


class TestPathConfig(unittest.TestCase):
    'Test gramex.conf.PathConfig'

    def setUp(self):
        self.a = info.home / 'config.a.yaml'
        self.b = info.home / 'config.b.yaml'
        self.temp = info.home / 'config.temp.yaml'
        self.imp = info.home / 'config.import.yaml'
        self.final = info.home / 'config.final.yaml'
        self.chain = AttrDict(
            base=info.home / 'config.template.base.yaml',
            child=info.home / 'config.template.child.yaml',
            subdir=info.home / 'dir/config.template.subdir.yaml',
        )
        self.conf1 = info.home / Path('conf1.test')
        self.conf2 = info.home / Path('conf2.test')

    def tearDown(self):
        unlink(self.conf1)
        unlink(self.conf2)

    def test_merge(self):
        'Config files are loaded and merged'
        unlink(self.temp)
        conf = ChainConfig([
            ('a', PathConfig(self.a)),
            ('b', PathConfig(self.b))])
        self.assertEqual(+conf, PathConfig(self.final))

    def test_update(self):
        'Config files are updated on change'
        conf = ChainConfig(temp=PathConfig(self.temp))

        # When the file is missing, config is empty
        unlink(self.temp)
        self.assertEqual(+conf, {})

        # When the file is blank, config is empty
        with self.temp.open('w') as out:
            out.write(six.text_type(''))
        self.assertEqual(+conf, {})

        # Once created, it is automatically reloaded
        data = AttrDict(a=1, b=2)
        with self.temp.open('w') as out:
            yaml.dump(data, out)
        self.assertEqual(+conf, data)

        # Deleted file is detected
        self.temp.unlink()
        self.assertEqual(+conf, {})

    def test_chain_update(self):
        'Chained config files are changed on update'
        # Set up a configuration with 2 files -- conf1.test and conf2.test.
        with self.conf1.open(mode='w', encoding='utf-8') as handle:
            yaml.dump({'url': {}}, handle)
        with self.conf2.open(mode='w', encoding='utf-8') as handle:
            yaml.dump({'url': {'a': 1}}, handle)

        conf = ChainConfig()
        conf.conf1 = PathConfig(self.conf1)
        conf.conf2 = PathConfig(self.conf2)
        self.assertEqual(+conf, {'url': {'a': 1}})

        # Change conf2.test and ensure that its original contents are replaced,
        # not just merged with previous value
        with self.conf2.open(mode='w', encoding='utf-8') as handle:
            yaml.dump({'url': {'b': 10}}, handle)
        self.assertEqual(+conf, {'url': {'b': 10}})

    def test_import(self):
        'Check if config files are imported'
        conf_imp = ChainConfig(conf=PathConfig(self.imp))
        conf_b = ChainConfig(conf=PathConfig(self.b))

        # When temp is missing, config matches b
        unlink(self.temp)
        self.assertEqual(+conf_imp, +conf_b)

        # Once temp file is created, it is automatically imported
        data = AttrDict(a=1, b=2)
        with self.temp.open('w') as out:
            yaml.dump(data, out)
        result = +conf_b
        result.update(data)
        self.assertEqual(+conf_imp, result)

        # Once removed, it no longer used
        unlink(self.temp)
        self.assertEqual(+conf_imp, +conf_b)

    def test_variables(self):
        'Templates interpolate string variables'
        # Create configuration with 2 layers and a subdirectory import
        conf = +ChainConfig(
            base=PathConfig(self.chain.base),
            child=PathConfig(self.chain.child),
        )
        # Custom variables are deleted after use
        self.assertFalse('variables' in conf)
        for key in ['base', 'child', 'subdir']:
            # {.} maps to YAML file's directory
            self.assertEqual(conf['%s_DOT' % key], str(self.chain[key].parent))
            # $YAMLPATH maps to YAML file's directory
            self.assertEqual(conf['%s_YAMLPATH' % key], str(self.chain[key].parent))
            # $YAMLURL is the relative path to YAML file's directory
            self.assertEqual(conf['%s_YAMLURL' % key], conf['%s_YAMLURL_EXPECTED' % key])
            # Environment variables are present by default
            self.assertEqual(conf['%s_HOME' % key], os.environ.get('HOME', ''))
            # Non-existent variables map to ''
            self.assertEqual(conf['%s_NONEXISTENT' % key], os.environ.get('NONEXISTENT', ''))
            # Custom variables are applied
            self.assertEqual(conf['%s_THIS' % key], key)
            # Custom variables are inherited. Defaults do not override
            self.assertEqual(conf['%s_ROOT' % key], conf.base_ROOT)
            # Default variables are set
            self.assertEqual(conf['%s_DEFAULT' % key], key)
            # Functions run and override values
            self.assertEqual(conf['%s_FUNCTION' % key], key)
            # Default functions "underride" values
            self.assertEqual(conf['%s_DEFAULT_FUNCTION' % key], 'base')
            # Derived variables
            self.assertEqual(conf['%s_DERIVED' % key], '%s/derived' % key)
            # $URLROOT is the frozen to base $YAMLURL
            self.assertEqual(conf['%s_YAMLURL_VAR' % key], conf['%s_YAMLURL_VAR_EXPECTED' % key])


class TestConfig(unittest.TestCase):
    def test_walk_dict(self):
        'Test gramex.config.walk with dicts'
        o = yaml.load('''
            a:
                b:
                    c: 1
                    d: 2
                e: 3
                f:
                    g:
                        h: 4
                        i: 5
                j: 6
            k: 7
        ''', Loader=AttrDictYAMLLoader)
        result = list(walk(o))
        self.assertEqual(
            [key for key, val, node in result],
            list('cdbehigfjak'))
        self.assertEqual(
            [val for key, val, node in result],
            [o.a.b.c, o.a.b.d, o.a.b, o.a.e, o.a.f.g.h, o.a.f.g.i, o.a.f.g,
             o.a.f, o.a.j, o.a, o.k])
        self.assertEqual(
            [node for key, val, node in result],
            [o.a.b, o.a.b, o.a, o.a, o.a.f.g, o.a.f.g, o.a.f,
             o.a, o.a, o, o])

    def test_walk_list(self):
        'Test gramex.config.walk with lists'
        o = yaml.load('''
            - 1
            - 2
            - 3
        ''', Loader=AttrDictYAMLLoader)
        result = list(walk(o))
        self.assertEqual(result, [
            (0, 1, [1, 2, 3]),
            (1, 2, [1, 2, 3]),
            (2, 3, [1, 2, 3])])

        o = yaml.load('''
            -
                x: 1
            -
                x: 2
            -
                x: 3
        ''', Loader=AttrDictYAMLLoader)
        result = list(walk(o))
        self.assertEqual(
            [('x', 1), (0, {'x': 1}),
             ('x', 2), (1, {'x': 2}),
             ('x', 3), (2, {'x': 3})],
            [(key, val) for key, val, node in result])

    def test_merge(self):
        'Test gramex.config.merge'
        def check(a, b, c):
            'Check if merge(a, b) is c. Parameters are in YAML'
            old = yaml.load(a, Loader=AttrDictYAMLLoader)
            new = yaml.load(b, Loader=AttrDictYAMLLoader)
            # merging a + b gives c
            self.assertEqual(
                yaml.load(c, Loader=AttrDictYAMLLoader),
                merge(old, new))
            # old and new are unchanged
            self.assertEqual(old, yaml.load(a, Loader=AttrDictYAMLLoader))
            self.assertEqual(new, yaml.load(b, Loader=AttrDictYAMLLoader))

        check('x: 1', 'y: 2', 'x: 1\ny: 2')
        check('x: {a: 1}', 'x: {a: 2}', 'x: {a: 2}')
        check('x: {a: 1}', 'x: null', 'x: null')
        check('x: {a: 1}', 'x: {b: 2}', 'x: {a: 1, b: 2}')
        check('x: {a: {p: 1}}', 'x: {a: {q: 1}, b: 2}', 'x: {a: {p: 1, q: 1}, b: 2}')
        check('x: {a: {p: 1}}', 'x: {a: null, b: null}', 'x: {a: null, b: null}')
