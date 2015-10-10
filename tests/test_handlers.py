import os
import io
import sys
import requests
import markdown
import unittest
import subprocess
from gramex.transforms import badgerfish


class TestGramex(unittest.TestCase):
    'Base class to test Gramex running as a subprocess'

    def setUp(self):
        self.folder = os.path.dirname(os.path.abspath(__file__))
        DEVNULL = getattr(subprocess, 'DEVNULL', open(os.devnull, 'w'))
        self.process = subprocess.Popen(
            # TODO: ensure that you run the right gramex
            [sys.executable, '-m', 'gramex'],
            cwd=self.folder,
            stdout=DEVNULL,
        )

    def get(self, url):
        return requests.get('http://localhost:9999' + url)

    def tearDown(self):
        self.process.terminate()


class TestDirectoryHandler(TestGramex):
    'Test gramex.handlers.DirectoryHandler'

    def check(self, url, path=None, code=200, text=None):
        r = self.get(url)
        self.assertEqual(r.status_code, code, url)
        if text is not None:
            self.assertIn(text, r.text, url)
        if path is not None:
            with open(os.path.join(self.folder, path), 'rb') as file:
                self.assertEqual(r.content, file.read(), url)
        return r

    def test_directory_handler(self):
        'Test DirectoryHandler'
        self.check('/dir/noindex/', code=404)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/index.html', path='dir/index.html')
        self.check('/dir/noindex/text.txt', path='dir/text.txt')
        self.check('/dir/noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/index/', code=200, text='subdir/</a>')
        self.check('/dir/index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/index/index.html', path='dir/index.html')
        self.check('/dir/index/text.txt', path='dir/text.txt')
        self.check('/dir/index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-index/', path='dir/index.html')
        self.check('/dir/default-present-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-present-index/index.html', path='dir/index.html')
        self.check('/dir/default-present-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-index/', code=200, text='subdir/</a>')
        self.check('/dir/default-missing-index/subdir/', code=200, text='text.txt</a>')
        self.check('/dir/default-missing-index/index.html', path='dir/index.html')
        self.check('/dir/default-missing-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-noindex/', path='dir/index.html')
        self.check('/dir/default-present-noindex/subdir/', code=404)
        self.check('/dir/default-present-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-present-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-noindex/', code=404)
        self.check('/dir/default-missing-noindex/subdir/', code=404)
        self.check('/dir/default-missing-noindex/index.html', path='dir/index.html')
        self.check('/dir/default-missing-noindex/text.txt', path='dir/text.txt')
        self.check('/dir/default-missing-noindex/subdir/text.txt', path='dir/subdir/text.txt')

        with io.open(os.path.join(self.folder, 'dir/markdown.md'), 'r', encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))
        with io.open(os.path.join(self.folder, 'dir/badgerfish.yaml'), 'r', encoding='utf-8') as f:
            self.check('/dir/transform/badgerfish.yaml', text=badgerfish(f.read()))
