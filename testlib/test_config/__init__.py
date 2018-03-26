# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import csv
import six
import yaml
import socket
import inspect
import logging
import unittest
import gramex
from pathlib import Path
from nose.tools import eq_, ok_
from orderedattrdict import AttrDict
from yaml.constructor import ConstructorError
from gramex.config import ChainConfig, PathConfig, walk, merge, ConfigYAMLLoader, _add_ns
from gramex.config import recursive_encode, TimedRotatingCSVHandler

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
    # Test gramex.conf.ChainConfig

    def test_attrdict(self):
        # ChainConfig is an AttrDict
        conf = ChainConfig(a=AttrDict(), b=AttrDict())
        conf.a.x = 1
        conf.a.y = 2
        eq_(conf, {'a': {'x': 1, 'y': 2}, 'b': {}})
        conf.b.x = 3
        conf.b.y = 4
        eq_(conf, {'a': {'x': 1, 'y': 2}, 'b': {'x': 3, 'y': 4}})

    def test_overlay(self):
        # +ChainConfig updates configs successively
        conf = ChainConfig()
        conf.a = AttrDict()
        conf.b = AttrDict()
        conf.a.x = 1
        conf.a.y = 2
        conf.b.x = 2
        eq_(+conf, {'x': 2, 'y': 2})
        conf.b.x = None
        eq_(+conf, {'y': 2})


class TestPathConfig(unittest.TestCase):
    # Test gramex.conf.PathConfig

    def setUp(self):
        self.a = info.home / 'config.a.yaml'
        self.b = info.home / 'config.b.yaml'
        self.temp = info.home / 'config.temp.yaml'
        self.imports = info.home / 'config.imports.yaml'
        self.imp = info.home / 'config.import.yaml'
        self.ns = info.home / 'config.namespace.yaml'
        self.final = info.home / 'config.final.yaml'
        self.chain = AttrDict(
            base=info.home / 'config.template.base.yaml',
            child=info.home / 'config.template.child.yaml',
            subdir=info.home / 'dir/config.template.subdir.yaml',
        )
        self.conf1 = info.home / Path('conf1.test')
        self.conf2 = info.home / Path('conf2.test')
        self.condition = info.home / 'config.condition.yaml'
        self.importmerge = info.home / 'config.importmerge.yaml'

        self.error = info.home / 'config.error.yaml'
        self.missing = info.home / 'config.missing.yaml'
        self.empty = info.home / 'config.empty.yaml'
        self.string = info.home / 'config.string.yaml'
        self.random = info.home / 'config.random.yaml'

    def tearDown(self):
        unlink(self.conf1)
        unlink(self.conf2)

    def test_random(self):
        # * in keys is replaced with a random 5-char alphanumeric
        conf = PathConfig(self.random)
        for key, val in conf.random.items():
            regex = re.compile(val.replace('*', '[A-Za-z0-9]{5}'))
            ok_(regex.match(key))

    def test_merge(self):
        # Config files are loaded and merged
        unlink(self.temp)
        conf = ChainConfig([
            ('a', PathConfig(self.a)),
            ('b', PathConfig(self.b))])
        eq_(+conf, PathConfig(self.final))

    def test_default(self):
        # Missing, empty or malformed config files return an empty AttrDict
        conf = ChainConfig([
            ('missing', PathConfig(self.missing)),
            ('error', PathConfig(self.error)),
            ('empty', PathConfig(self.empty)),
            ('string', PathConfig(self.string)),
        ])
        eq_(+conf, AttrDict())

    def test_update(self):
        # Config files are updated on change
        conf = ChainConfig(temp=PathConfig(self.temp))

        # When the file is missing, config is empty
        unlink(self.temp)
        eq_(+conf, {})

        # When the file is blank, config is empty
        with self.temp.open('w') as out:
            out.write(six.text_type(''))
        eq_(+conf, {})

        # Once created, it is automatically reloaded
        data = AttrDict(a=1, b=2)
        with self.temp.open('w') as out:
            yaml.dump(data, out)
        eq_(+conf, data)

        # Deleted file is detected
        self.temp.unlink()
        eq_(+conf, {})

    def test_chain_update(self):
        # Chained config files are changed on update
        # Set up a configuration with 2 files -- conf1.test and conf2.test.
        with self.conf1.open(mode='w', encoding='utf-8') as handle:
            yaml.dump({'url': {}}, handle)
        with self.conf2.open(mode='w', encoding='utf-8') as handle:
            yaml.dump({'url': {'a': 1}}, handle)

        conf = ChainConfig()
        conf.conf1 = PathConfig(self.conf1)
        conf.conf2 = PathConfig(self.conf2)
        eq_(+conf, {'url': {'a': 1}})

        # Change conf2.test and ensure that its original contents are replaced,
        # not just merged with previous value
        with self.conf2.open(mode='w', encoding='utf-8') as handle:
            yaml.dump({'url': {'b': 10}}, handle)
        eq_(+conf, {'url': {'b': 10}})

    def test_import(self):
        # Check if config files are imported
        conf_imp = ChainConfig(conf=PathConfig(self.imp))
        conf_b = ChainConfig(conf=PathConfig(self.b))

        # When temp is missing, config matches b
        unlink(self.temp)
        eq_(+conf_imp, +conf_b)

        # Once temp file is created, it is automatically imported
        data = AttrDict(a=1, b=2)
        with self.temp.open('w') as out:
            yaml.dump(data, out)
        result = +conf_b
        result.update(data)
        eq_(+conf_imp, result)

        # Once removed, it no longer used
        unlink(self.temp)
        eq_(+conf_imp, +conf_b)

    def test_add_ns(self):
        # Test _add_ns functionality
        eq_(_add_ns({'x': 1}, '*', 'a'), {'a:x': 1})
        eq_(_add_ns({'x': {'y': 1}}, 'x', 'a'), {'x': {'a:y': 1}})
        eq_(_add_ns({'x': {'y': 1}}, ['*', 'x'], 'a'), {'a:x': {'a:y': 1}})
        eq_(_add_ns({'x': {'y': 1}}, ['x', '*'], 'a'), {'a:x': {'a:y': 1}})

    def test_variables(self):
        # Templates interpolate string variables
        # Create configuration with 2 layers and a subdirectory import
        conf = +ChainConfig(
            base=PathConfig(self.chain.base),
            child=PathConfig(self.chain.child),
        )
        # Custom variables are deleted after use
        ok_('variables' not in conf)
        for key in ['base', 'child', 'subdir']:
            # {.} maps to YAML file's directory
            eq_(conf['%s_DOT' % key], str(self.chain[key].parent))
            # $YAMLPATH maps to YAML file's directory
            eq_(conf['%s_YAMLPATH' % key], str(self.chain[key].parent))
            # $YAMLURL is the relative path to YAML file's directory
            eq_(conf['%s_YAMLURL' % key], conf['%s_YAMLURL_EXPECTED' % key])
            # Environment variables are present by default
            eq_(conf['%s_HOME' % key], os.environ.get('HOME', ''))
            # Non-existent variables map to ''
            eq_(conf['%s_NONEXISTENT' % key], os.environ.get('NONEXISTENT', ''))
            # Custom variables are applied
            eq_(conf['%s_THIS' % key], key)
            # Custom variables are inherited. Defaults do not override
            eq_(conf['%s_ROOT' % key], conf.base_ROOT)
            # Default variables are set
            eq_(conf['%s_DEFAULT' % key], key)
            # Functions run and override values
            eq_(conf['%s_FUNCTION' % key], key)
            # Default functions "underride" values
            eq_(conf['%s_DEFAULT_FUNCTION' % key], 'base')
            # Functions can use variables using gramex.config.variables
            eq_(conf['%s_FUNCTION_VAR' % key], conf.base_ROOT + key)
            # Derived variables
            eq_(conf['%s_DERIVED' % key], '%s/derived' % key)
            # $URLROOT is the frozen to base $YAMLURL
            eq_(conf['%s_YAMLURL_VAR' % key], conf['%s_YAMLURL_VAR_EXPECTED' % key])
            # $GRAMEXPATH is the gramex path
            gramex_path = os.path.dirname(inspect.getfile(gramex))
            eq_(conf['%s_GRAMEXPATH' % key], gramex_path)
            # $GRAMEXAPPS is the gramex apps path
            eq_(conf['%s_GRAMEXAPPS' % key], os.path.join(gramex_path, 'apps'))
            # $GRAMEXHOST is the socket.gethostname
            eq_(conf['%s_GRAMEXHOST' % key], socket.gethostname())
        # Imports do not override, but do setdefault
        eq_(conf['path'], str(self.chain['base'].parent))
        eq_(conf['subpath'], str(self.chain['subdir'].parent))

        # Check if variable types are preserved
        eq_(conf['numeric'], 1)
        eq_(conf['boolean'], True)
        eq_(conf['object'], {'x': 1})
        eq_(conf['list'], [1, 2])

        # Check if variables of different types are string substituted
        eq_(conf['numeric_subst'], '/1')
        eq_(conf['boolean_subst'], '/True')
        # Actually, conf['object_subst'] is "/AttrDict([('x', 1)])". Let's not test that.
        # eq_(conf['object_subst'], "/{'x': 1}")
        eq_(conf['list_subst'], '/[1, 2]')

        # Check condition variables
        for key, val in conf['conditions'].items():
            eq_('is-' + key, val)

    def test_if(self):
        conf = PathConfig(self.condition)
        for key, val in conf.items():
            eq_(val['expected'], val['actual'])

    def test_import_merge(self):
        conf = PathConfig(self.importmerge)
        for key, val in conf.items():
            eq_(val['expected'], val['actual'])


class TestConfig(unittest.TestCase):
    def test_walk_dict(self):
        # Test gramex.config.walk with dicts
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
        ''', Loader=ConfigYAMLLoader)
        result = list(walk(o))
        eq_(
            [key for key, val, node in result],
            list('cdbehigfjak'))
        eq_(
            [val for key, val, node in result],
            [o.a.b.c, o.a.b.d, o.a.b, o.a.e, o.a.f.g.h, o.a.f.g.i, o.a.f.g,
             o.a.f, o.a.j, o.a, o.k])
        eq_(
            [node for key, val, node in result],
            [o.a.b, o.a.b, o.a, o.a, o.a.f.g, o.a.f.g, o.a.f,
             o.a, o.a, o, o])

    def test_walk_list(self):
        # Test gramex.config.walk with lists
        o = yaml.load('''
            - 1
            - 2
            - 3
        ''', Loader=ConfigYAMLLoader)
        result = list(walk(o))
        eq_(result, [
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
        ''', Loader=ConfigYAMLLoader)
        result = list(walk(o))
        eq_(
            [('x', 1), (0, {'x': 1}),
             ('x', 2), (1, {'x': 2}),
             ('x', 3), (2, {'x': 3})],
            [(key, val) for key, val, node in result])

    def test_merge(self):
        # Test gramex.config.merge
        def check(a, b, c, mode='overwrite'):
            '''Check if merge(a, b) is c. Parameters are in YAML'''
            old = yaml.load(a, Loader=ConfigYAMLLoader)
            new = yaml.load(b, Loader=ConfigYAMLLoader)
            # merging a + b gives c
            eq_(
                yaml.load(c, Loader=ConfigYAMLLoader),
                merge(old, new, mode))
            # new is unchanged
            # eq_(old, yaml.load(a, Loader=ConfigYAMLLoader))
            eq_(new, yaml.load(b, Loader=ConfigYAMLLoader))

        check('x: 1', 'y: 2', 'x: 1\ny: 2')
        check('x: {a: 1}', 'x: {a: 2}', 'x: {a: 2}')
        check('x: {a: 1}', 'x: null', 'x: null')
        check('x: {a: 1}', 'x: {b: 2}', 'x: {a: 1, b: 2}')
        check('x: {a: {p: 1}}', 'x: {a: {q: 1}, b: 2}', 'x: {a: {p: 1, q: 1}, b: 2}')
        check('x: {a: {p: 1}}', 'x: {a: null, b: null}', 'x: {a: null, b: null}')
        check('x: 1', 'x: 2', 'x: 1', mode='underwrite')
        check('x: {a: 1, c: 3}', 'x: {a: 2, b: 2}', 'x: {a: 1, c: 3, b: 2}', mode='underwrite')

        # Check basic behaviour
        eq_(merge({'a': 1}, {'a': 2}), {'a': 2})
        eq_(merge({'a': 1}, {'a': 2}, mode='setdefault'), {'a': 1})
        eq_(merge({'a': {'b': 1}}, {'a': {'b': 2}}), {'a': {'b': 2}})
        eq_(merge({'a': {'b': 1}}, {'a': {'b': 2}}, mode='setdefault'), {'a': {'b': 1}})

        # Ensure int keys will work
        eq_(merge({1: {1: 1}}, {1: {1: 2}}), {1: {1: 2}})
        eq_(merge({1: {1: 1}}, {1: {1: 2}}, mode='setdefault'), {1: {1: 1}})

    def test_no_duplicates(self):
        dup_keys = '''
            a: 1
            a: 2
        '''
        eq_(yaml.load(dup_keys), {'a': 2})
        with self.assertRaises(ConstructorError):
            yaml.load(dup_keys, Loader=ConfigYAMLLoader)

        dup_keys = '''
            a:
                b: 1
                b: 2
        '''
        eq_(yaml.load(dup_keys), {'a': {'b': 2}})
        with self.assertRaises(ConstructorError):
            yaml.load(dup_keys, Loader=ConfigYAMLLoader)

    def test_recursive_encode(self):
        ua, ub = 'α', 'β'
        ba, bb = ua.encode('utf-8'), ub.encode('utf-8')
        src = {ua: ub, True: [1, ub], None: {ua: ub, '': {ua: 1, ub: 0.1}}}
        out = {ba: bb, True: [1, bb], None: {ba: bb, b'': {ba: 1, bb: 0.1}}}
        recursive_encode(src)
        eq_(src, out)


class TestTimedRotatingCSVHandler(unittest.TestCase):
    csv1 = info.home / 'file1.csv'
    csv2 = info.home / 'file2.csv'

    def test_handler(self):
        csv1 = TimedRotatingCSVHandler(
            filename=str(self.csv1),
            keys=['a', 'b', 'c'],
            encoding='utf-8'
        )
        csv2 = TimedRotatingCSVHandler(
            filename=str(self.csv2),
            keys=['a', 'b', 'c'],
            encoding='utf-8'
        )

        test1 = logging.getLogger('test1')
        test1.setLevel(logging.INFO)
        test1.addHandler(csv1)

        test2 = logging.getLogger('test2')
        test2.setLevel(logging.WARNING)
        test2.addHandler(csv1)
        test2.addHandler(csv2)

        # Do not test unicode. Python 2.7 csv writer does not support it
        test1.info({'a': 'a', 'b': 1, 'c': -0.1})       # noqa: 0.1 is not magic
        test2.info({'a': 'na', 'b': 'na', 'c': 'na'})
        test1.warn({'a': True, 'b': False, 'c': None})
        test2.warn({'b': '\n\na,bt\n'})

        with self.csv1.open() as handle:
            eq_(list(csv.reader(handle)), [
                ['a', '1', '-0.1'],
                ['True', 'False', ''],
                ['', '\n\na,bt\n', ''],
            ])
        with self.csv2.open() as handle:
            eq_(list(csv.reader(handle)), [
                ['', '\n\na,bt\n', ''],
            ])

    @classmethod
    def tearDown(cls):
        for name in ['test1', 'test2']:
            logger = logging.getLogger(name)
            for handler in logger.handlers:
                handler.close()
        for path in [cls.csv1, cls.csv2]:
            if path.exists():
                path.unlink()
