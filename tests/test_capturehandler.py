from __future__ import unicode_literals

import io
import os
import re
import time
import logging
from PIL import Image
from nose.tools import eq_, ok_
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.high_level import extract_text_to_fp
from gramex.handlers import Capture
from . import TestGramex, server

_captures = {}


def get_capture(name, **kwargs):
    '''Return a cached Capture() object constructed with kwargs'''
    if name in _captures:
        return _captures[name]
    capture = _captures[name] = Capture(**kwargs)
    end_time, delay = time.time() + 5, 0.05
    logging.info('Waiting for capture.js...')
    while not capture.started:
        if time.time() > end_time:
            raise RuntimeError('capture.js took too long to start')
        time.sleep(delay)
    return capture


def get_text(content):
    infile, outfile = io.BytesIO(content), io.BytesIO()
    extract_text_to_fp(infile, outfile)
    return outfile.getvalue().decode('utf-8')


def normalize(s):
    '''
    Ignore Unicode characters. These are normalized by PhantomJS.
    Ignore whitespaces. They may translate to \t sometimes.
    Just stick to ASCII.
    '''
    return re.sub(r'[^\x33-\x7f]+', '', s)


class TestCaptureHandler(TestGramex):
    size = (1200, 768)
    max_colors = 65536
    url = '/dir/capture'

    @classmethod
    def setupClass(cls):
        cls.capture = get_capture('default', port=9402)
        cls.folder = os.path.dirname(os.path.abspath(__file__))

    def test_capture_init(self):
        ok_(self.capture.started)

    def fetch(self, url, code=200, **kwargs):
        r = self.get(url, **kwargs)
        eq_(r.status_code, code)
        return r

    def check_filename(self, result, name):
        disp = result.headers.get('Content-Disposition', '')
        eq_(disp, 'attachment; filename="%s"' % name)

    def check_pdf(self, content):
        # Ensure that each line in dir/capture.html is in the text
        # On Linux, spaces seem to appear as tabs. Normalize that
        text = normalize(get_text(content))
        source = os.path.join(self.folder, 'dir', 'capture.html')
        for line in io.open(source, 'r', encoding='utf-8'):
            frag = normalize(line.strip())
            # Only compare non-HTML non-empty lines
            if len(frag) > 0 and '<' not in line:
                self.assertIn(frag, text)

    def test_capture_pdf(self):
        # Test capture library API
        content = self.capture.pdf(url=server.base_url + self.url)
        self.check_pdf(content)

        # Test service: relative and absolute URLs
        for url in (server.base_url + self.url, '../' + self.url, self.url):
            result = self.fetch('/capture', params={'url': url})
            self.check_filename(result, 'screenshot.pdf')
            self.check_pdf(result.content)

        # delay=. After 500ms, page changes text and color to blue
        # file=.  Changes filename
        result = self.fetch('/capture', params={'url': self.url, 'delay': 600, 'file': 'delay'})
        self.check_filename(result, 'delay.pdf')
        self.assertIn('Blueblock', normalize(get_text(result.content)))

        # --format and --orientation
        result = self.fetch('/capture', params={'url': self.url, 'format': 'A3',
                                                'orientation': 'landscape'})
        parser = PDFParser(io.BytesIO(result.content))
        page = next(PDFPage.create_pages(PDFDocument(parser)))
        self.assertIn(page.attrs['MediaBox'], (
            [0, 0, 1188, 842],      # noqa: Chrome uses 1188 x 842 for A3
            [0, 0, 1191, 842],      # noqa: PhantomJS uses 1191 x 842 for A3
        ))

        # cookie=. The Cookie is printed on the screen via JS
        result = self.fetch('/capture', params={'url': self.url + '?show-cookie',
                                                'cookie': 'a=x'})
        self.assertIn('a=x', normalize(get_text(result.content)))
        # Cookie: header is the same as ?cookie=.
        # Old request cookies vanish. Only new ones remain
        result = self.fetch('/capture', params={'url': self.url + '?show-cookie'},
                            headers={'Cookie': 'b=z'})
        result_text = normalize(get_text(result.content))
        self.assertIn('js:cookie=b=z', result_text)
        self.assertIn('server:cookie=b=z', result_text)

    def check_img(self, content, color=None, min=100, size=None):
        img = Image.open(io.BytesIO(content)).convert(mode='RGBA')
        if size:
            eq_(img.size, size)
        # dir/index.html has a style="color:red" block in it. So check that there's enough red
        if color:
            # Ensure that the color is present at least in min pixels in the image
            colors = {clr: freq for freq, clr in img.getcolors(self.max_colors)}
            self.assertGreater(colors.get(color, 0), min)

    def test_capture_png(self):
        content = self.capture.png(url=server.base_url + self.url)
        self.check_img(content, color=(255, 0, 0, 255), min=100, size=self.size)

        # Check file=, ext=, width=, height=
        result = self.fetch('/capture', params={
            'url': self.url, 'width': 600, 'height': 1200, 'file': 'capture', 'ext': 'png'})
        self.check_filename(result, 'capture.png')
        self.check_img(result.content, size=(600, 1200))

        # selector=. has a 100x100 green patch
        result = self.fetch('/capture', params={
            'url': self.url, 'selector': '.subset', 'ext': 'png'})
        self.check_img(result.content, color=(0, 128, 0, 255), min=9000, size=(100, 100))

    def test_capture_jpg(self):
        # TODO: check colors
        content = self.capture.jpg(url=server.base_url + self.url)
        self.check_img(content)

        # Check file=, ext=, width=, height=
        result = self.fetch('/capture', params={
            'url': self.url, 'width': 800, 'height': 1000, 'file': 'capture', 'ext': 'jpg'})
        self.check_filename(result, 'capture.jpg')
        self.check_img(result.content, size=(800, 1000))
