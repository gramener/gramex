from . import TestGramex
from nose.tools import ok_
from gramex.apps.ui import bootstrap_path, uicomponents_path


class TestUI(TestGramex):
    def test_url_priority(self):
        text = self.check('/ui/sass', headers={'Content-Type': 'text/css'}).text
        ok_('.color_arg{color:#000}' in text)
        ok_('.bootstrap_path{after:"' + bootstrap_path + '"}')
        ok_('.uicomponents_path{after:"' + uicomponents_path + '"}')
        ok_('.google_font{after:set()}')

        text = self.check('/ui/sass?color=red').text
        ok_('.color_arg{color:red}' in text)

        text = self.check('/ui/sass?font-family-base=lato').text
        ok_('.google_font{after:"{&#39;Lato&#39;}"}')
