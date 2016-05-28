import os
import shutil
import requests
import unittest
from pathlib import Path
from shutilwhich import which
from orderedattrdict import AttrDict
from six.moves.urllib.parse import urljoin
import gramex
from gramex.config import variables, PathConfig
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
                if '.git' not in root:
                    actual.add(os.path.join(root, filename))
        expected = {os.path.abspath(os.path.join(folder, filename))
                    for filename in expected_files}
        self.assertEqual(actual, expected)

        conf = +PathConfig(Path(self.appdir('apps.yaml')))
        self.assertTrue(appname in conf)
        self.assertTrue('target' in conf[appname])
        self.assertTrue('cmd' in conf[appname] or 'url' in conf[appname])
        self.assertTrue('installed' in conf[appname])
        self.assertTrue('time' in conf[appname].installed)


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

    def test_zip_url_contentdir(self):
        self.check_zip('zip-contentdir', contentdir=False, files={
            'common-root/dir1/dir1.txt', 'common-root/dir1/file.txt',
            'common-root/dir2/dir2.txt', 'common-root/dir2/file.txt'})

    def test_zip_flat(self):
        # This ZIP file has members directly under the root. Test such cases
        install(['zip-flat'], AttrDict(url=urljoin(server.base_url, 'install-test-flat.zip')))
        self.check_files('zip-flat', ['file1.txt', 'file2.txt'])
        self.check_uninstall('zip-flat')

    def test_url_in_cmd(self):
        install(['url-cmd', self.zip_url], AttrDict())
        self.check_files('url-cmd', {
            'dir1/dir1.txt', 'dir1/file.txt', 'dir2/dir2.txt', 'dir2/file.txt'})
        self.check_uninstall('url-cmd')

    def test_run(self):
        # When you call gramex run run-app --dir=dir1 --browser=False, ensure
        # that gramex.init() is run from dir1 and is passed --browser=False.
        # We do that by mocking gramex.init() with check_init()
        result = AttrDict()

        def check_init(**kwargs):
            result.cwd = os.getcwd()
            result.opts = kwargs.get('cmd', {}).get('app', {})

        install(['run-app', self.zip_url], AttrDict())
        old_init = gramex.init
        old_cwd = os.getcwd()
        setattr(gramex, 'init', check_init)
        run(['run-app'], AttrDict(dir='dir1', browser=False))
        setattr(gramex, 'init', old_init)
        os.chdir(old_cwd)
        self.assertEqual(result.cwd, self.appdir('run-app/dir1/'))
        self.assertEqual(result.opts.get('browser'), False)
        self.check_uninstall('run-app')

    def test_dir(self):
        dirpath = os.path.join(folder, 'dir', 'subdir')
        install(['dir'], AttrDict(url=dirpath))
        self.check_files('dir', os.listdir(dirpath))
        self.check_uninstall('dir')

    def test_dir(self):
        dirpath = os.path.join(folder, 'dir', 'subdir')
        install(['dir'], AttrDict(url=dirpath))
        self.check_files('dir', os.listdir(dirpath))
        self.check_uninstall('dir')

    def test_git_url(self):
        git_files = ['dir1/file.txt', 'dir1/file-dir1.txt', 'dir2/file.txt', 'dir2/file-dir2.txt']
        git_url, branch = 'http://code.gramener.com/s.anand/gramex.git', 'test-apps'
        try:
            requests.get(git_url)
        except requests.RequestException:
            self.skipTest('Unable to connect to code.gramener.com')

        cmd = 'git clone %s --branch %s --single-branch' % (git_url, branch)
        install(['git-url'], AttrDict(cmd=cmd))
        self.check_files('git-url', git_files)
        # TODO: Do not uninstall. Check if overwriting works.
        self.check_uninstall('git-url')

        cmd = 'git clone %s TARGET --branch %s --single-branch' % (git_url, branch)
        install(['git-url'], AttrDict(cmd=cmd))
        self.check_files('git-url', git_files)
        self.check_uninstall('git-url')

    def test_setup(self):
        dirpath = os.path.join(folder, 'dir', 'install')
        install(['setup'], AttrDict(url=dirpath))

        result = set()
        for root, dirs, files in os.walk(dirpath):
            for filename in files:
                path = os.path.join(root, filename)
                result.add(os.path.relpath(path, dirpath))

        if which('powershell'):
            result.add('powershell-setup.txt')
        if which('make'):
            result.add('makefile-setup.txt')
        if which('bash'):
            result.add('bash-setup.txt')
        if which('python'):
            result.add('python-setup.txt')
        if which('npm'):
            result.add('node_modules/gramex-npm-package/package.json')
            result.add('node_modules/gramex-npm-package/npm-setup.js')
        if which('bower'):
            result.add('bower_components/gramex-bower-package/bower.json')
            result.add('bower_components/gramex-bower-package/bower-setup.txt')
            result.add('bower_components/gramex-bower-package/.bower.json')
        self.check_files('setup', result)
        self.check_uninstall('setup')
