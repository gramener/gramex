from nose.tools import eq_
from nose.plugins.skip import SkipTest
from . import TestGramex


class TestPyNode(TestGramex):
    def runjs(self, code, result, **data):
        r = self.check('/pynode/run', data=dict(data, code=code)).json()
        # On Windows, if we install a lib, we need to restart node for require() to work.
        # For this, we need to kill the terminal that runs nosetests!
        # So, allow any test with lib= to fail -- by skipping. It should be fine next time.
        if 'lib' in data and isinstance(r['error'], dict):
            if r['error'].get('message', '').startswith('Cannot find module'):
                raise SkipTest(f'node_modules not installed: {data["lib"]}')
        eq_(r['error'], None)
        eq_(r['result'], result)

    def test_js(self):
        self.runjs('return Math.abs(x + y)', 5, x=5, y=-10)
        self.runjs('return x[y]', 'f', x='abcedfgh', y=5)

    def test_lib_lodash(self):
        self.runjs('return require("lodash").repeat(x, y)', 'x.x.x.x.', x='x.', y=4, lib='lodash')

    def test_lib_dayjs(self):
        self.runjs('return require("dayjs")(d).format("D-M-YY")', '1-2-21', d='2021-02-01',
                   lib='dayjs')

    def test_lib_moment(self):
        self.runjs('return require("moment")(d).format("D-M-YY")', '1-2-21', d='2021-02-01',
                   lib='moment')

    def test_lib_numeraljs(self):
        self.runjs('return require("numeraljs")(d)', {'_value': 2300}, d='2,300', lib='numeraljs')
