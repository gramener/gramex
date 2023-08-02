from gramex.http import BAD_REQUEST
from nose.tools import eq_, ok_
from . import TestGramex, etree

ns = {'svg': 'http://www.w3.org/2000/svg'}


class TestComicHandler(TestGramex):
    def test_aryan(self):
        r = self.check('/comic', data={'name': 'aryan', 'emotion': 'angry', 'pose': 'handsfolded'})
        tree = etree.fromstring(r.text)
        parts = tree.findall('svg:svg/svg:g/svg:svg/svg:svg/svg:g/svg:svg', namespaces=ns)
        # Aryan has two characters, each with at least a hundred parts (as of now)
        eq_(len(parts), 2)
        ok_(len(parts[0].findall('svg:path', namespaces=ns)) > 100)
        ok_(len(parts[1].findall('svg:path', namespaces=ns)) > 100)

    def test_ava(self):
        r = self.check('/comic', data={'name': 'ava', 'emotion': 'sad', 'pose': 'super'})
        tree = etree.fromstring(r.text)
        parts = tree.findall('svg:svg/svg:g/svg:svg/svg:svg/svg:g/svg:svg', namespaces=ns)
        # Ava has 2 parts with 5-12 paths
        eq_(len(parts), 2)
        ok_(5 <= len(parts[0].findall('svg:path', namespaces=ns)) <= 12)
        ok_(5 <= len(parts[1].findall('svg:path', namespaces=ns)) <= 12)

    def test_error(self):
        self.check('/comic', text='')
        self.check('/comic', data={'name': 'nonexistent'}, code=BAD_REQUEST)
