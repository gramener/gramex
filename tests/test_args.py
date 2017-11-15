# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
import json
from gramex.http import BAD_REQUEST
from . import TestGramex


class TestArgs(TestGramex):
    def test_args(self):
        # Check BaseHandler creates a self.args in unicode
        def f(query, args, **kwargs):
            r = self.get('/httpbin' + query, **kwargs)
            self.assertEqual(r.json()['args'], args)

        f('?高=λ', {'高': ['λ']})
        f('?高=λ&高=σ', {'高': ['λ', 'σ']})
        f('?高=', {'高': ['']})
        f('?高', {'高': ['']})
        f('?=&高=λ&兴=σ&兴=█', {'高': ['λ'], '兴': ['σ', '█'], '': ['']})
        f('?देश=भारत', {'देश': ['भारत']})

    def test_get_args(self):
        r = self.get('/func/get_arg?x=a&x=b&val=x&first=x&default=x')
        self.assertEqual(r.json(), {'val': 'b', 'first': 'a', 'default': 'b'})
        r = self.get('/func/get_arg?default=na&missing=na')
        self.assertEqual(r.json(), {'default': 'ok', 'missing': 'ok'})

    def check_argparse(self, query, result, *args, **kwargs):
        params = {'_q': json.dumps({'args': args, 'kwargs': kwargs})}
        r = self.get('/func/argparse' + query, params=params)
        if isinstance(result, six.string_types):
            self.assertEqual(r.status_code, BAD_REQUEST)
            self.assertIn(result, r.reason)
        else:
            result = r.json()
            result.pop('_q', None)
            self.assertEqual(result, result)

    def test_argparse(self):
        # Check BaseHandler.argparse
        f = self.check_argparse

        f('', {})
        f('?x=1', {'x': '1'})
        f('?x=1&x=2', {'x': '2'})
        f('?x=1&y=2', {'x': '1', 'y': 2})

        f('', {}, 'str')
        f('?x=1', {'x': '1'}, 'str')
        f('?x=1&x=2', {'x': '2'}, 'str')
        f('?x=1&y=2', {'x': '1', 'y': 2}, 'str')

        f('', {}, 'None')
        f('?x=1', {}, 'None')
        f('?x=1&y=2', {}, 'None')

        f('?x=1', {'x': ['1']}, 'list')
        f('?x=1&x=2', {'x': ['1', '2']}, 'list')
        f('?x=1&y=2', {'x': ['1'], 'y': ['2']}, 'list')

        f('', 'x: missing', 'x')
        f('?x=', {'x': ''}, 'x')
        f('?x=a', {'x': 'a'}, 'x')
        f('?x=a&x=b', {'x': 'b'}, 'x')
        f('?x=a', 'y: missing', 'x', 'y')
        f('?x=a&y=b', {'x': 'a', 'y': 'b'}, 'x', 'y')

        f('', {}, x={})
        f('?x=a', {'y': 'a'}, y={'name': 'x'})
        f('?x=a', 'y: missing', y={'required': True})
        f('?x=a', {'y': 1}, y={'default': 1})
        f('?x=a', {'y': True}, y={'default': True})
        f('?x=a', {'y': False}, y={'default': False})
        f('?x=a', {'y': False}, y={'default': False})

        f('?x=a', {'x': ['a']}, x={'nargs': '*'})
        f('?x=a&x=b&x=c', {'x': ['a', 'b', 'c']}, x={'nargs': '*'})
        f('?x=a&x=b&x=c', {'x': ['a']}, x={'nargs': 1})
        f('?x=a&x=b&x=c', {'x': ['a', 'b']}, x={'nargs': 2})
        f('?x=a&x=b&x=c', {'x': ['a', 'b', 'c', '', '']}, x={'nargs': 5})
        f('', {'x': ['', '', '']}, x={'nargs': 3})

        f('?x=1', {'x': 1}, x={'type': 'int'})
        f('?x=a', 'x: type error', x={'type': 'int'})
        f('?x=1&x=2&x=3', {'x': 3}, x={'type': 'int'})
        f('?x=1&x=2&x=3', {'x': [1, 2, 3]}, x={'nargs': '*', 'type': 'int'})
        f('?x=&x=0&x=3', {'x': [False, True, True]}, x={'nargs': '*', 'type': 'bool'})
        f('?x=1&x=2&x=a', 'x: type error', x={'nargs': '*', 'type': 'int'})

        f('?x=a', {'x': 'a'}, x={'choices': ['a', 'b']})
        f('?x=c', 'x: invalid choice', x={'choices': ['a', 'b']})
        f('?x=a&x=b&x=c', {'x': ['a', 'b']}, x={'nargs': 2, 'choices': ['a', 'b']})
        f('?x=a&x=c', 'x: invalid choice', x={'nargs': 2, 'choices': ['a', 'b']})
        f('?x=1&x=2&x=3', {'x': [1, 2, 3]}, x={'nargs': '*', 'type': 'int', 'choices': [1, 2, 3]})
        f('?x=1&x=2&x=3', 'x: invalid choice', x={'nargs': '*', 'type': 'int', 'choices': [1, 2]})
