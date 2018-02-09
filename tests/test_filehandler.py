# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import os
import six
import json
import pathlib
import requests
import markdown
from gramex.http import OK, FORBIDDEN, METHOD_NOT_ALLOWED
from orderedattrdict import AttrDict
from gramex.transforms import badgerfish
from . import server, tempfiles, TestGramex


def setUpModule():
    # Create a unicode filename to test if FileHandler's directory listing shows it
    folder = os.path.dirname(os.path.abspath(__file__))
    tempfiles.unicode_file = os.path.join(folder, 'dir', 'subdir', u'unicode–file.txt')
    with io.open(tempfiles.unicode_file, 'w', encoding='utf-8') as out:
        out.write(six.text_type(tempfiles.unicode_file))

    # Create a symlink to test if these are displayed in a directory listing without errors
    # If os.symlink does not exist (Linux), raises an AttributeError
    # If os.symlink does not have permission (Windows 10), raises an OSError
    # In either case, ignore it
    try:
        symlink = os.path.join(folder, 'dir', 'subdir', 'symlink.txt')
        os.symlink(os.path.join(folder, 'gramex.yaml'), symlink)
        tempfiles.symlink = symlink
    except (OSError, AttributeError):
        pass


class TestFileHandler(TestGramex):
    def test_directoryhandler(self):
        # DirectoryHandler == FileHandler
        from gramex.handlers import DirectoryHandler, FileHandler
        self.assertEqual(DirectoryHandler, FileHandler)

    def test_filehandler(self):
        def adds_slash(url, check):
            self.assertFalse(url.endswith('/'), 'redirect_with_slash url must not end with /')
            r = self.get(url)
            if check:
                self.assertTrue(r.url.endswith('/'), url)
                redirect_codes = (301, 302)
                self.assertIn(r.history[0].status_code, redirect_codes, url)
            else:
                self.assertEqual(len(r.history), 0)

        self.check('/dir/noindex/', code=404)
        adds_slash('/dir/noindex/subdir', False)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/index.html', path='dir/index.html')
        self.check('/dir/noindex/text.txt', path='dir/text.txt')
        self.check('/dir/noindex/subdir/text.txt', path='dir/subdir/text.txt')

        # Check unicode filenames only if pathlib supports them
        try:
            pathlib.Path(tempfiles.unicode_file)
            self.check(u'/dir/noindex/subdir/unicode–file.txt')
        except UnicodeError:
            pass

        self.check('/dir/index/', text='subdir/</a>')
        adds_slash('/dir/index/subdir', True)
        self.check('/dir/index/subdir/', code=OK, text='text.txt</a>')
        self.check('/dir/index/index.html', path='dir/index.html')
        self.check('/dir/index/text.txt', path='dir/text.txt')
        self.check('/dir/index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-present-index/', path='dir/index.html')
        adds_slash('/dir/default-present-index/subdir', True)
        self.check('/dir/default-present-index/subdir/', text='text.txt</a>')
        self.check('/dir/default-present-index/index.html', path='dir/index.html')
        self.check('/dir/default-present-index/text.txt', path='dir/text.txt')
        self.check('/dir/default-present-index/subdir/text.txt', path='dir/subdir/text.txt')

        self.check('/dir/default-missing-index/', text='subdir/</a>')
        adds_slash('/dir/default-missing-index/subdir', True)
        self.check('/dir/default-missing-index/subdir/', text='text.txt</a>')
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

        self.check('/dir/single-file/', path='dir/text.txt')
        self.check('/dir/single-file/alpha', path='dir/text.txt')
        self.check('/dir/single-file/alpha/beta', path='dir/text.txt')

        self.check('/dir/data', path='dir/data.csv', headers={
            'Content-Type': 'text/plain',
            'Content-Disposition': None
        })

    def test_args(self):
        self.check('/dir/args/?高=σ', text=json.dumps({'高': ['σ']}))
        self.check('/dir/args/?高=σ&高=λ&س=►', text=json.dumps(
            {'高': ['σ', 'λ'], 'س': ['►']}, sort_keys=True))

    def test_index_template(self):
        # Custom index_template is used in directories
        self.check('/dir/indextemplate/', text='<title>indextemplate</title>')
        self.check('/dir/indextemplate/', text='text.txt</a>')
        # Custom index_template is used in sub-directories
        self.check('/dir/indextemplate/subdir/', text='<title>indextemplate</title>')
        self.check('/dir/indextemplate/subdir/', text='text.txt</a>')
        # Non-existent index templates default to Gramex filehandler.template.html
        self.check('/dir/no-indextemplate/', text='File list by Gramex')

    def test_url_normalize(self):
        self.check('/dir/normalize/slash/index.html/', path='dir/index.html')
        self.check('/dir/normalize/dot/index.html', path='dir/index.html')
        self.check('/dir/normalize/dotdot/index.html', path='dir/index.html')

    def test_filehandle_errors(self):
        self.check('/nonexistent', code=404)
        self.check('/dir/nonexistent-file', code=404)
        self.check('/dir/noindex/../../gramex.yaml', code=404)
        self.check('/dir/noindex/../nonexistent', code=404)

    def test_markdown(self):
        with (server.info.folder / 'dir/markdown.md').open(encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))

    def test_transform_badgerfish(self):
        handler = AttrDict(file=server.info.folder / 'dir/badgerfish.yaml')
        with (server.info.folder / 'dir/badgerfish.yaml').open(encoding='utf-8') as f:
            result = yield badgerfish(f.read(), handler)
            self.check('/dir/transform/badgerfish.yaml', text=result)
            self.check('/dir/transform/badgerfish.yaml', text='imported file α')

    def test_transform_template(self):
        # gramex.yaml has configured template.* to take handler and x as params
        self.check('/dir/transform/template.txt?x=►', text='x – ►')
        self.check('/dir/transform/template.txt?x=λ', text='x – λ')
        self.check('/dir/transform/template-handler.txt')

    def test_template(self):
        self.check('/dir/template/index-template.txt?arg=►', text='– ►')
        self.check('/dir/template/non-index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-true/index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-true/non-index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-index/index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-index/non-index-template.txt', path='dir/non-index-template.txt')

    def test_merge(self):
        self.check('/dir/merge.txt', text='Α.TXT\nΒ.Html\n', headers={
            'Content-Type': 'text/plain; charset=UTF-8'
        })
        self.check('/dir/merge.html', text='Β.HTML\nΑ.Txt\n', headers={
            'Content-Type': 'text/html; charset=UTF-8'
        })

    def test_pattern(self):
        self.check('/dir/pattern/alpha/text', path='dir/alpha.txt')
        self.check('/dir/pattern/text/text', path='dir/text.txt')
        self.check('/dir/pattern/subdir/text/text', path='dir/subdir/text.txt')
        self.check('/dir/pattern/text/na/text', code=404)
        self.check('/dir/pattern/text.na/text', code=404)
        self.check('/dir/pattern/index.web', path='dir/index.html')
        self.check('/dir/pattern/subdir/sub', path='dir/subdir/text.txt')

    def test_etag(self):
        # Single static files compute an Etag
        self.check('/dir/index/index.html', headers={'Etag': True})
        # Directory templates also compute an Etag
        self.check('/dir/index/', headers={'Etag': True})
        # Non-existent files do not have an etag
        self.check('/dir/noindex/', code=404, headers={'Etag': False})

    def test_ignore(self):
        self.check('/dir/index/gramex.yaml', code=FORBIDDEN)
        self.check('/dir/index/.hidden', code=FORBIDDEN)
        self.check('/dir/index/ignore-file.txt')
        self.check('/dir/ignore-file/ignore-file.txt', code=FORBIDDEN)
        self.check('/dir/index/ignore-list.txt')
        self.check('/dir/ignore-list/ignore-list.txt', code=FORBIDDEN)
        self.check('/dir/ignore-list/ignore-list.ext1', code=FORBIDDEN)
        self.check('/dir/ignore-list/ignore-list.EXT2', code=FORBIDDEN)
        self.check('/dir/allow-file/gramex.yaml')
        self.check('/dir/allow-ignore/ignore-file.txt')
        self.check('/server.py', code=FORBIDDEN)     # Ignore .py files by default
        self.check('/dir/index/.allow')              # But .allow is allowed
        # Paths are resolved before ignoring
        self.check('/dir/ignore-all-except/', path='dir/index.html')

    def test_methods(self):
        config = {
            '/methods/get-only': {
                OK: ('get',),
                METHOD_NOT_ALLOWED: ('head', 'post', 'put', 'delete', 'patch', 'options'),
            },
            '/methods/head-put-delete': {
                OK: ('head', 'put', 'delete'),
                METHOD_NOT_ALLOWED: ('get', 'post', 'patch', 'options'),
            }
        }
        for url, results in config.items():
            for code, methods in results.items():
                for method in methods:
                    r = getattr(requests, method)(server.base_url + url)
                    self.assertEqual(r.status_code, code,
                                     '%s %s should return %d' % (method, url, code))

    def test_headers(self):
        self.check('/header/', headers={
            'X-FileHandler-Header': 'updated',
            'X-FileHandler': 'updated',
            'X-FileHandler-Base': 'base',
        })
        self.check('/headerdict/alpha.txt', headers={'Root': 'a', 'Sub': 'a', 'All': 'x'})
        self.check('/headerdict/beta.html', headers={'Root': 'b', 'Sub': 'b', 'All': 'x'})
        self.check('/headerdict/data.csv', headers={'Root': 'x', 'All': 'x'})
        self.check('/headerdict/install/gramex-npm-package/package.json', headers={
            'Root': 'x', 'Sub': 'x'})
        self.check('/headerdict/install/gramex-bower-package/bower.json', headers={
            'Root': 'x', 'Sub': 'y'})
