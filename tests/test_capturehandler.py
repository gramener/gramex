from __future__ import unicode_literals

import io
import os
import re
import time
import logging
from PIL import Image
from unittest import SkipTest
from nose.tools import eq_, ok_
from unicodedata import normalize
from pdfminer.high_level import extract_text_to_fp
from gramex.handlers import Capture
from . import TestGramex, server

_captures = {}

def get_capture(name, **kwargs):
    '''Return a cached Capture() object constructed with kwargs'''
    if name in _captures:
        return _captures[name]
    capture = _captures[name] = Capture(**kwargs)
    end_time = time.time() + 5
    logging.info('Waiting for capture.js...')
    while not capture.started:
        if time.time() > end_time:
            raise RuntimeError('capture.js took too long to start')
        time.sleep(0.05)
    return capture


def get_text(pdf):
    infile, outfile = io.BytesIO(pdf), io.BytesIO()
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
    @classmethod
    def setupClass(cls):
        cls.capture = get_capture('default')
        cls.folder = os.path.dirname(os.path.abspath(__file__))

    def test_capture_init(self):
        ok_(self.capture.started)

    def check_pdf_contents(self, result):
        # Ensure that each line in dir/index.html is in the text
        # On Linux, spaces seem to appear as tabs. Normalize that
        text = normalize(get_text(result))
        for line in io.open(os.path.join(self.folder, 'dir', 'index.html'), 'r', encoding='utf-8'):
            frag = normalize(line.strip())
            # Only compare non-HTML non-empty lines
            if len(frag) > 0 and '<' not in line:
                self.assertIn(frag, text)

    def test_capture_pdf(self):
        # Test capture library
        result = self.capture.pdf(url=server.base_url + '/dir/')
        self.check_pdf_contents(result)
        # Test service: relative and absolute URLs
        for url in (server.base_url + '/dir/', '../dir/', '/dir/'):
            result2 = self.get('/capture', params={'url': url})
            self.check_pdf_contents(result2.content)

    def check_img_contents(self, result, colors=True):
        img = Image.open(io.BytesIO(result)).convert(mode='RGBA')
        eq_(img.size, (1200, 768))
        # dir/index.html has a style="color:red" block in it. So check that there's enough red
        if colors:
            colors = {color: freq for freq, color in img.getcolors(65536)}
            self.assertGreater(colors.get((255, 0, 0, 255), 0), 100)

    def test_capture_png(self):
        result = self.capture.png(url=server.base_url + '/dir/')
        self.check_img_contents(result)
        result = self.get('/capture', params={'url': '/dir/', 'ext': 'png'})
        self.check_img_contents(result.content)

    def test_capture_jpg(self):
        # TODO: check colors
        result = self.capture.jpg(url=server.base_url + '/dir/')
        self.check_img_contents(result, colors=False)
        result = self.get('/capture', params={'url': '/dir/', 'ext': 'jpg'})
        self.check_img_contents(result.content, colors=False)

    def test_capture_gif(self):
        raise SkipTest('Not supported on Linux? TBD')
