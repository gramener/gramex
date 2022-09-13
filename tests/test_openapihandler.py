import gramex.cache
from . import TestGramex
from nose.tools import eq_, ok_


class TestOpenAPIHandler(TestGramex):
    expected = gramex.cache.open('openapiresponse.yaml', rel=True)

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
            'url': '..',
            'description': 'Server-description'
        }])

        self.check_functionhandler(spec)
        self.check_formhandler(spec)

    def check_functionhandler(self, spec):
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
                'in': 'query', 'description': '',
                'schema': {'type': 'array', 'items': {'type': 'integer'}, 'default': [0]},
            }, params['li3'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '',
                'schema': {'type': 'array', 'items': {'type': 'number'}, 'default': [0.0]},
            }, params['lf3'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '',
                'schema': {'type': ['string'], 'default': []},
            }, params['l1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': 'First value',
                'schema': {'type': ['integer'], 'default': 0},
            }, params['i1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': 'Second value',
                'schema': {'type': ['integer'], 'default': 0},
            }, params['i2'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '',
                'schema': {'type': ['string'], 'default': 'Total'},
            }, params['s1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '',
                'schema': {'type': ['integer'], 'default': 0},
            }, params['n1'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '',
                'schema': {'type': ['string'], 'default': 0},
            }, params['n2'])
            self.assertDictContainsSubset({
                'in': 'header', 'description': '',
                'schema': {'type': ['string'], 'default': ''},
            }, params['h'])
            self.assertDictContainsSubset({
                'in': 'query', 'description': '',
                'schema': {'type': ['integer'], 'default': 200},
            }, params['code'])

            self.check_response(conf['responses'])

    def check_response(self, resp):
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

    def check_formhandler(self, spec):
        ok_('/openapi/form' in spec['paths'])
        eq_(spec['paths']['/openapi/form'], self.expected['/openapi/form'])
