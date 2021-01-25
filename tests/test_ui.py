from . import TestGramex
from nose.tools import ok_


class TestUI(TestGramex):
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
