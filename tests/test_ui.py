from . import TestGramex
from gramex.http import MOVED_PERMANENTLY, FOUND
from nose.tools import ok_


class TestUI(TestGramex):
    def test_ui_lib(self):
        cdn = 'https://cdn.jsdelivr.net/npm'

        def check(source, url, code=FOUND):
            self.check(source, allow_redirects=False, code=code, headers={'Location': url})

        check('/ui/d3/dist/d3.min.js', f'{cdn}/d3/dist/d3.min.js')
        check('/ui/d3?v=1', f'{cdn}/d3', code=MOVED_PERMANENTLY)
        check('/ui/d3v5', f'{cdn}/d3@5')
        check('/ui/bootstrap', f'{cdn}/bootstrap@4')
        check('/ui/bootstrap?v=1', f'{cdn}/bootstrap@4', code=MOVED_PERMANENTLY)
        check(
            '/ui/bootstrap/dist/css/bootstrap.min.css?v=1',
            f'{cdn}/bootstrap@4/dist/css/bootstrap.min.css',
            code=MOVED_PERMANENTLY,
        )
        check('/ui/bootstrap5', f'{cdn}/bootstrap@5')
        check('/ui/daterangepickerv3', f'{cdn}/daterangepicker@3')
        check('/ui/url-search-params', f'{cdn}/@ungap/url-search-params@0.1')

    def test_ui_sass(self):
        text = self.check('/uitest/sass', headers={'Content-Type': 'text/css'}).text
        ok_('.color_arg{color:#000}' in text)
        ok_('.google_font{after:set()}')

        text = self.check('/uitest/sass?color=red').text
        ok_('.color_arg{color:red}' in text)

        text = self.check('/uitest/sass?font-family-base=lato').text
        ok_('.google_font{after:"{&#39;Lato&#39;}"}', 'auto-adds Google Fonts')

        text = self.check('/ui/bootstraptheme.css?colorabc=purple').text
        ok_('--colorabc: purple' in text, '?colorabc adds --colorabc as a theme color')

    def test_ui_theme(self):
        text = self.check('/ui/theme/default.scss', headers={'Content-Type': 'text/css'}).text
        ok_('--primary' in text, 'Compiles SASS')

    def check_vars(self, url):
        text = self.check(url + '?primary=blue&color-a=red&color-b=&@import=sass/a.scss').text
        ok_('--primary: blue' in text, 'vars: URL vars used')
        ok_('--a: red' in text, 'vars: color- adds colors')
        ok_('--b:' not in text, 'vars: ignores empty values')
        ok_('.ui-import-a{color:blue}' in text, 'vars: cascaded into @import')

    def test_vars(self):
        self.check_vars('/ui/theme/default.scss')

    def test_sass2(self):
        self.check_vars('/uitest/sass2')
