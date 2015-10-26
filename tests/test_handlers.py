import os
import sys
import json
import requests
import markdown
import unittest
import subprocess
from pathlib import Path
from orderedattrdict import AttrDict
from gramex.transforms import badgerfish


info = AttrDict(
    folder=Path(__file__).absolute().parent,
    process=None,
)


def setUpModule():
    'Run Gramex in this folder using the current gramex.conf.yaml'
    # Ensure that PYTHONPATH has this repo and ONLY this repo
    env = dict(os.environ)
    env['PYTHONPATH'] = str(info.folder.parent)
    info.process = subprocess.Popen(
        [sys.executable, '-m', 'gramex'],
        cwd=str(info.folder),
        env=env,
        stdout=getattr(subprocess, 'DEVNULL', open(os.devnull, 'w')),
    )


def tearDownModule():
    'Terminate Gramex'
    info.process.terminate()


class TestGramex(unittest.TestCase):
    'Base class to test Gramex running as a subprocess'

    def get(self, url, **kwargs):
        return requests.get('http://localhost:9999' + url, **kwargs)

    def check(self, url, path=None, code=200, text=None):
        r = self.get(url)
        self.assertEqual(r.status_code, code, url)
        if text is not None:
            self.assertIn(text, r.text, '%s: %s != %s' % (url, text, r.text))
        if path is not None:
            with (info.folder / path).open('rb') as file:
                self.assertEqual(r.content, file.read(), url)
        return r

    def test_url_priority(self):
        self.check('/path/abc', text='/path/.*')
        self.check('/path/file', text='/path/file')
        self.check('/path/dir', text='/path/.*')
        self.check('/path/dir/', text='/path/dir/.*')
        self.check('/path/dir/abc', text='/path/dir/.*')
        self.check('/path/dir/file', text='/path/dir/file')
        self.check('/path/priority', text='/path/priority')


class TestDirectoryHandler(TestGramex):
    'Test gramex.handlers.DirectoryHandler'

    def test_directory(self):
        'Test DirectoryHandler'
        def adds_slash(url, check):
            self.assertFalse(url.endswith('/'), 'redirect_with_slash url must not end with /')
            r = self.get(url)
            if check:
                self.assertTrue(r.url.endswith('/'), url)
                self.assertIn(r.history[0].status_code, (301, 302), url)
            else:
                self.assertEqual(len(r.history), 0)

        self.check('/dir/noindex/', code=404)
        adds_slash('/dir/noindex/subdir', False)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/index.html', path='dir/index.html')
        self.check('/dir/noindex/text.txt', path='dir/text.txt')
        self.check('/dir/noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/index/', code=200, text='subdir/</a>')
        adds_slash('/dir/index/subdir', True)
        self.check('/dir/index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/index/index.html', path='dir/index.html')
        self.check('/dir/index/text.txt', path='dir/text.txt')
        self.check('/dir/index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-index/', path='dir/index.html')
        adds_slash('/dir/default-present-index/subdir', True)
        self.check('/dir/default-present-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-present-index/index.html', path='dir/index.html')
        self.check('/dir/default-present-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-index/', code=200, text='subdir/</a>')
        adds_slash('/dir/default-missing-index/subdir', True)
        self.check('/dir/default-missing-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-missing-index/index.html', path='dir/index.html')
        self.check('/dir/default-missing-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-noindex/', path='dir/index.html')
        adds_slash('/dir/default-present-noindex/subdir', False)
        self.check('/dir/default-present-noindex/subdir/', code=404)
        self.check('/dir/default-present-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-present-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-noindex/', code=404)
        adds_slash('/dir/default-missing-noindex/subdir', False)
        self.check('/dir/default-missing-noindex/subdir/', code=404)
        self.check('/dir/default-missing-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-missing-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/noindex/binary.bin', path='dir/binary.bin')

        self.check('/dir/args/?x=1', text=json.dumps({'x': ['1']}))
        self.check('/dir/args/?x=1&x=2&y=3', text=json.dumps({'x': ['1', '2'], 'y': ['3']},
                                                             sort_keys=True))

    def test_transforms(self):
        with (info.folder / 'dir/markdown.md').open(encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))

        handler = AttrDict(file=info.folder / 'dir/badgerfish.yaml')
        with (info.folder / 'dir/badgerfish.yaml').open(encoding='utf-8') as f:
            self.check('/dir/transform/badgerfish.yaml', text=badgerfish(f.read(), handler))
            self.check('/dir/transform/badgerfish.yaml', text='imported file')

    def test_default_config(self):
        'Check default gramex.yaml configuration'
        r = self.get('/reload-config', allow_redirects=False)
        self.assertIn(r.status_code, (301, 302), '/reload-config works and redirects')
