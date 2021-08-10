from . import TestGramex
from nose.tools import eq_, ok_


class TestOpenAPIHandler(TestGramex):
    def has_param(self, params, **kwargs):
        items = kwargs.items()
        for param in params:
            if items <= param.items():
                return True
        return False

    def test_openapi(self):
        # OpenAPI spec is a JSON response
        spec = self.check('/openapi/spec').json()
        # OpenAPI spec version matches
        eq_(spec['openapi'], '3.0.2')
        # spec.info comes from gramex.yaml OpenAPIHandler kwargs
        # .info is from gramex.yaml > openapi/spec
        eq_(spec['info'], {
            'title': 'OpenAPI-title',
            'version': 'OpenAPI-version',
            'description': 'OpenAPI-description',
        })
        # spec.servers comes from gramex.yaml OpenAPIHandler kwargs
        eq_(spec['servers'], [{
            'url': '.',
            'description': 'Server-description'
        }])
        # /openapi/func path exists
        ok_('/openapi/func' in spec['paths'])
        path = spec['paths']['/openapi/func']
        for request in ('get', 'post'):
            ok_(request in path)
            conf = path[request]
            # Summary is based on function name
            eq_(conf['summary'], 'Openapi Func: FunctionHandler')
            # Description is as per utils.test_function
            eq_(conf['description'], '\nThis is a **Markdown** docstring.\n')
            # Argument types, defaults, required as per utils.test_function
            params = {param['name']: param for param in conf['parameters']}
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'required': True,
                'schema': {'type': 'array', 'items': {'type': 'integer'}},
            }, params['li1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'required': True,
                'schema': {'type': 'array', 'items': {'type': 'number'}},
            }, params['lf1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': 'List of ints', 'required': True,
                'schema': {'type': 'array', 'items': {'type': 'integer'}},
            }, params['li2'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': 'List of floats', 'required': True,
                'schema': {'type': 'array', 'items': {'type': 'number'}},
            }, params['lf2'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': [0],
                'schema': {'type': 'array', 'items': {'type': 'integer'}},
            }, params['li3'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': [0.0],
                'schema': {'type': 'array', 'items': {'type': 'number'}},
            }, params['lf3'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': [],
                'schema': {'type': ['string']},
            }, params['l1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': 'First value', 'default': 0,
                'schema': {'type': ['integer']},
            }, params['i1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': 'Second value', 'default': 0,
                'schema': {'type': ['integer']},
            }, params['i2'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': 'Total',
                'schema': {'type': ['string']},
            }, params['s1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': 0,
                'schema': {'type': ['integer']},
            }, params['n1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': 0,
                'schema': {'type': ['string']},
            }, params['n2'])
            self.assertDictContainsSubset({
                'in': 'header', 'description': '', 'default': '',
                'schema': {'type': ['string']},
            }, params['h'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '', 'default': 200,
                'schema': {'type': ['integer']},
            }, params['code'])

            resp = conf['responses']
            # 400 response has description from gramex.yaml
            self.assertDictContainsSubset({
                'description': 'You served a bad request',
                'content': {'text/html': {'example': 'Bad request'}}
            }, resp['400'])
            # Rest should have default error responses
            self.assertDictContainsSubset({
                'description': 'Successful Response',
                'content': {'application/json': {}}
            }, resp['200'])
            self.assertDictContainsSubset({
                'description': 'Not authorized',
                'content': {'text/html': {'example': 'Not authorized'}}
            }, resp['401'])
