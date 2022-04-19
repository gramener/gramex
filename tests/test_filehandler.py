import io
import os
import json
import pathlib
import requests
import markdown
from gramex.http import OK, FORBIDDEN, METHOD_NOT_ALLOWED
from orderedattrdict import AttrDict
from gramex.ml import r
from gramex.transforms import badgerfish, rmarkdown
from nose.tools import ok_, eq_
from nose.plugins.skip import SkipTest
from . import server, tempfiles, TestGramex, folder


def write(path, text):
    with io.open(path, 'w', encoding='utf-8') as out:
        out.write(text)


def setUpModule():
    # Create a unicode filename to test if FileHandler's directory listing shows it
    tempfiles.unicode_file = os.path.join(folder, 'dir', 'subdir', 'unicode–file.txt')
    write(tempfiles.unicode_file, str(tempfiles.unicode_file))

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
            self.assertFalse(url.endswith('/'), 'adds_slash url must not end with /')
            r = self.get(url + '?高=σ&λ=►')
            if check:
                self.assertTrue(r.url.endswith(url + '/?%E9%AB%98=%CF%83&%CE%BB=%E2%96%BA'))
                self.assertIn(r.history[0].status_code, redirect_codes, url)
            else:
                self.assertEqual(len(r.history), 0)

        redirect_codes = (301, 302)
        self.check('/dir/noindex/', code=404)
        adds_slash('/dir/noindex/subdir', False)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/index.html', path='dir/index.html')
        self.check('/dir/noindex/text.txt', path='dir/text.txt')
        self.check('/dir/noindex/subdir/text.txt', path='dir/subdir/text.txt')

        # Check default filenames support default.template.html and default.tmpl.html
        self.check('/dir/def1/', text='7\ndefault.template.html')
        self.check('/dir/def2/', text='7\ndefault.tmpl.html')

        # Check unicode filenames only if pathlib supports them
        try:
            pathlib.Path(tempfiles.unicode_file)
            self.check('/dir/noindex/subdir/unicode–file.txt')
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

        self.check('/dir/image.JPG', path='dir/image.JPG', headers={
            'Content-Type': 'image/jpeg'
        })

        r = self.get('/dir/index/subdir', allow_redirects=False, headers={
            'X-Request-URI': 'https://x.com/a/dir/index/subdir'})
        ok_(r.status_code in redirect_codes)
        eq_(r.headers['Location'], 'https://x.com/a/dir/index/subdir/')

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
        # Add non-existent template and check live load
        tempfiles.index_template = os.path.join(folder, 'nonexistent.template.html')
        write(tempfiles.index_template, 'newtemplate: $path $body')
        self.check('/dir/no-indextemplate/', text='newtemplate')

    def test_url_normalize(self):
        self.check('/dir/normalize/slash/index.html/', path='dir/index.html')
        self.check('/dir/normalize/dot/index.html', path='dir/index.html')
        self.check('/dir/normalize/dotdot/index.html', path='dir/index.html')

    def test_filehandler_errors(self):
        self.check('/nonexistent', code=404)
        self.check('/dir/nonexistent-file', code=404)
        self.check('/dir/noindex/subdir/', code=404)
        self.check('/dir/noindex/../nonexistent', code=404)
        self.check('/dir/noindex/../../gramex.yaml', code=403)

    def test_gramex_cache_rel(self):
        self.check('/dir/cache.template.html', text='α.txt')

    def test_markdown(self):
        with (server.info.folder / 'dir/markdown.md').open(encoding='utf-8') as f:
            self.check('/dir/transform/markdown.md', text=markdown.markdown(f.read()))

    def test_rmarkdown(self):
        # rmarkdown must be installed
        ok_(r('"rmarkdown" %in% installed.packages()')[0],
            'rmarkdown must be installed. Run conda install -c r r-rmarkdown')

        def _callback(f):
            f = f.result()
            return f

        path = server.info.folder / 'dir/rmarkdown.Rmd'
        handler = AttrDict(file=path)
        result = rmarkdown('', handler).add_done_callback(_callback)
        try:
            self.check('/dir/transform/rmarkdown.Rmd', text=result)
        except AssertionError:
            raise SkipTest('TODO: Once NumPy & rpy2 work together, remove this SkipTest. #259')
        htmlpath = str(server.info.folder / 'dir/rmarkdown.html')
        tempfiles[htmlpath] = htmlpath

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

    def test_sass(self):
        for dir in ('/dir/transform-sass', '/dir/sass-file'):
            for file in ('import.scss', 'import.sass'):
                text = self.check(f'{dir}/{file}?primary=red&color-alpha=purple').text
                ok_('.ui-import-a{color:red}' in text, f'{dir}.{file}: import a.scss with vars')
                ok_('--primary: red' in text, f'{dir}.{file}: import bootstrap with vars')
                ok_('--alpha: purple' in text, f'{dir}.{file}: import gramexui with vars')
        self.check('/dir/transform-sass/a.scss?primary=blue', text='.ui-import-a{color:blue}')
        self.check('/dir/transform-sass/b.scss?primary=blue', text='.ui-import-b{color:blue}')

    def test_vue(self):
        for dir in ('/dir/transform-vue', '/dir/vue-file'):
            for name in ('a', 'b'):
                url = f'{dir}/comp-{name}.vue'
                text = self.check(url, timeout=30).text
                ok_(f'Component: {name}' in text, f'{url}: has component name')
                ok_(f'//# sourceMappingURL=comp-{name}.vue?map' in text, f'{url}: has sourcemap')
                source = self.check(url + '?map').json()
                eq_(source['version'], 3)
        # TODO: Invalid file should generate a compilation failure
        # TODO: Changing file should recompile

    def test_ts(self):
        for dir in ('/dir/transform-ts', '/dir/ts-file'):
            for name in ('a', 'b'):
                url = f'{dir}/{name}.ts'
                text = self.check(url, timeout=30).text
                # TypeScript transpiles into ES3 by default, converting const to var.
                # So check for 'var a =' in output, though source uses 'const a ='

                ok_(f'var {name} = ' in text, f'{url}: has correct content')
                ok_(f'//# sourceMappingURL={name}.ts?map' in text, f'{url}: has sourcemap')
                source = self.check(url + '?map').json()
                eq_(source['version'], 3)

    def test_template(self):
        self.check('/dir/template/index-template.txt?arg=►', text='– ►')
        self.check('/dir/template/non-index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-true/index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-true/non-index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-index/index-template.txt?arg=►', text='– ►')
        self.check('/dir/template-index/non-index-template.txt', path='dir/non-index-template.txt')

        # Treat *.template.html and *.tmpl.html files as templates (via default FileHandler)
        self.check('/filetest.template.html', text='555')
        self.check('/filetest.tmpl.html', text='555')

    def test_subtemplate(self):
        tempfiles.module = os.path.join(folder, 'dir', 'tempmodule.txt')
        write(tempfiles.module, '{{ x }} {{ y }}')
        for dir in ['transform', 'template', 'template-true']:
            r = self.check('/dir/%s/template.sub.txt' % dir)
            self.assertIn('Hello world', r.text)
            self.assertIn('Second phrase', r.text)
        write(tempfiles.module, '{{ y }} {{ x }}')
        for dir in ['transform', 'template', 'template-true']:
            r = self.check('/dir/%s/template.sub.txt' % dir)
            self.assertIn('Hello world', r.text)
            self.assertIn('phrase Second', r.text)

    def test_merge(self):
        self.check('/dir/merge.txt', text='Α.TXT\nΒ.Html\n', headers={
            'Content-Type': 'text/plain; charset=UTF-8'
        })
        self.check('/dir/merge.html', text='Β.HTML\nΑ.Txt\n', headers={
            'Content-Type': 'text/html; charset=UTF-8'
        })

    def test_map(self):
        # '/dir/map/': dir/index.html
        self.check('/dir/map/', path='dir/index.html')
        # '/dir/map/(.*)/(.*)/(.*)': 'dir/{0}{1}{2}'
        self.check('/dir/map/cap/ture/.js', path='dir/capture.js')
        self.check('/dir/map/al/ph/a.txt', text='Α.TXT')    # Capitalized alpha.txt
        self.check('/dir/map/x/y/z', code=404)
        # '/dir/map/url': 'dir/{file}{mid}.{ext}'
        self.check('/dir/map/url?file=template', path='dir/template.txt')
        self.check('/dir/map/url?file=template&file=x', path='dir/template.txt')
        self.check('/dir/map/url?file=template&mid=.sub', path='dir/template.sub.txt')
        self.check('/dir/map/url?file=index&ext=html', path='dir/index.html')
        self.check('/dir/map/url?file=nonexistent', code=404)
        self.check('/dir/map/url', code=404)
        # '/dir/map/(?P<ext>txt)/(.*)': 'dir/{1}.{ext}'
        self.check('/dir/map/txt/template', path='dir/template.txt')
        self.check('/dir/map/txt/capture?ext=js', code=404)
        # '/dir/map/(?P<n>\w+)/(.*)': 'dir/{n}.{1}'
        self.check('/dir/map/index/html', path='dir/index.html')
        self.check('/dir/map/alpha/def', code=404)
        # '/dir/map/(.*)': 'dir/subdir/{0}.txt'
        self.check('/dir/map/template', path='dir/subdir/template.txt')
        self.check('/dir/map/text', path='dir/subdir/text.txt')
        self.check('/dir/map/abc', code=404)
        # '': 'dir/{file}{mid}.{ext}'
        self.check('/dir/map2/?file=template', path='dir/template.txt')
        self.check('/dir/map2/?file=template&file=x', path='dir/template.txt')
        self.check('/dir/map2/?file=template&mid=.sub', path='dir/template.sub.txt')
        self.check('/dir/map2/?file=index&ext=html', path='dir/index.html')
        self.check('/dir/map2/?file=nonexistent', code=404)
        self.check('/dir/map2/', code=404)

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
        self.check('/dir/index/.hidedir/file.txt', code=FORBIDDEN)
        self.check('/dir/index/subdir/gramex.yaml', code=FORBIDDEN)
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

    def test_parent(self):
        # Eliminate parent directory references
        from gramex import variables
        self.check('/{}'.format(variables['GRAMEXDATA']), code=404)

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
        # ToDo: Fix with FileHandler 2
        # self.check('/headerdict/install/gramex-bower-package/bower.json', headers={
        #     'Root': 'x', 'Sub': 'y'})
