import json
import markdown
from orderedattrdict import AttrDict
from gramex.transforms import badgerfish
from . import server
from .test_handlers import TestGramex


setUpModule = server.start_gramex
tearDownModule = server.stop_gramex
redirect_codes = (301, 302)


class TestFileHandler(TestGramex):
    'Test FileHandler'

    def test_directoryhandler(self):
        'DirectoryHandler == FileHandler'
        from gramex.handlers import DirectoryHandler, FileHandler
        self.assertEqual(DirectoryHandler, FileHandler)

    def test_filehandler(self):
        'Test FileHandler'
        def adds_slash(url, check):
            self.assertFalse(url.endswith('/'), 'redirect_with_slash url must not end with /')
            r = self.get(url)
            if check:
                self.assertTrue(r.url.endswith('/'), url)
                self.assertIn(r.history[0].status_code, redirect_codes, url)
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

        self.check('/dir/data', code=200, path='dir/data.csv', headers={
            'Content-Type': 'text/plain',
            'Content-Disposition': None
        })

    def test_filehandle_errors(self):
        self.check('/nonexistent', code=404)
        self.check('/dir/nonexistent-file', code=404)
        self.check('/dir/noindex/../gramex.yaml', code=403)
        self.check('/dir/noindex/../nonexistent', code=404)

    def test_markdown(self):
        with (server.info.folder / 'dir/markdown.md').open(encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))

    def test_badgerfish(self):
        handler = AttrDict(file=server.info.folder / 'dir/badgerfish.yaml')
        with (server.info.folder / 'dir/badgerfish.yaml').open(encoding='utf-8') as f:
            result = yield badgerfish(f.read(), handler)
            self.check('/dir/transform/badgerfish.yaml', text=result)
            self.check('/dir/transform/badgerfish.yaml', text='imported file')

    def test_template(self):
        # gramex.yaml has configured template.* to take handler and x as params
        self.check('/dir/transform/template.txt?x=1', text='x = 1')
        self.check('/dir/transform/template.txt?x=abc', text='x = abc')

    def test_merge(self):
        self.check('/dir/merge.txt', text='ALPHA.TXT\nBeta.Html\n', headers={
            'Content-Type': 'text/plain'
        })
        self.check('/dir/merge.html', text='BETA.HTML\nAlpha.Txt\n', headers={
            'Content-Type': 'text/html'
        })
