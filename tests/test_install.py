import os
import unittest
from orderedattrdict import AttrDict
from six.moves.urllib.parse import urljoin
from gramex.config import variables
from gramex.install import install, uninstall, run
from . import server

folder = os.path.dirname(os.path.abspath(__file__))


class TestInstall(unittest.TestCase):
    zip_url = urljoin(server.base_url, 'install-test.zip')
    zip_file = os.path.join(folder, 'install-test.zip')

    @staticmethod
    def appdir(appname):
        return os.path.abspath(os.path.join(variables['GRAMEXDATA'], 'apps', appname))

    def check_files(self, appname, expected_files):
        '''app/ directory should have expected files'''
        folder = self.appdir(appname)
        actual = set()
        for root, dirs, files in os.walk(folder):
            for filename in files:
                actual.add(os.path.join(root, filename))
        expected = {os.path.abspath(os.path.join(folder, filename))
                    for filename in expected_files}
        self.assertEqual(actual, expected)

    def check_uninstall(self, appname):
        '''Check that appname exists. Uninstall appname. It should be removed'''
        folder = self.appdir(appname)
        self.assertTrue(os.path.exists(folder))
        uninstall([appname], {})
        self.assertFalse(os.path.exists(folder))

    def check_zip(self, appname, files, **params):
        '''Test installing and uninstalling a zipfile via URL and as a file'''
        args = AttrDict(params)
        for url, suffix in ((self.zip_url, '-url'), (self.zip_file, '-file')):
            args.url = url
            subappname = appname + suffix
            install([subappname], args)
            self.check_files(subappname, files)
            self.check_uninstall(subappname)

    def test_zip(self):
        self.check_zip('zip', files={
            'dir1/dir1.txt', 'dir1/file.txt', 'dir2/dir2.txt', 'dir2/file.txt'})

    def test_zip_rootdir(self):
        self.check_zip('zip-dir1', rootdir='dir1', files={'dir1.txt', 'file.txt'})
        self.check_zip('zip-dir2', rootdir='dir2', files={'dir2.txt', 'file.txt'})

    def test_zip_url_contentdir(self):
        self.check_zip('zip-contentdir', contentdir=False, files={
            'common-root/dir1/dir1.txt', 'common-root/dir1/file.txt',
            'common-root/dir2/dir2.txt', 'common-root/dir2/file.txt'})

    def test_zip_flat(self):
        install(['zip-flat'], AttrDict(url=urljoin(server.base_url, 'install-test-flat.zip')))
        self.check_files('zip-flat', ['file1.txt', 'file2.txt'])
        self.check_uninstall('zip-flat')

    def test_dir(self):
        dirpath = os.path.join(folder, 'dir', 'subdir')
        install(['dir'], AttrDict(url=dirpath))
        self.check_files('dir', os.listdir(dirpath))
        self.check_uninstall('dir')
