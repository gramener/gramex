# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import pandas as pd
from nose.tools import eq_, ok_, assert_raises
from PIL import Image
from gramex.ml import r
from . import folder


def test_init():
    # This part of the test leads to a segfault on Linux. Run only on Windows
    if sys.platform == 'win32':
        # R_HOME is set to a non-existent directory
        os.environ['R_HOME'] = os.path.join(folder, 'R')
        with assert_raises(RuntimeError):
            import rpy2.robjects
    # But Gramex uses Conda PATH
    r('ls()')
    import rpy2.rinterface
    # Note: in your machine, ensure "conda" is part of your Anaconda PATH
    ok_('conda' in rpy2.rinterface.R_HOME)


def test_command():
    eq_(r('1 + 2')[0], 3)
    eq_(r('sum(c(1,2,3))')[0], 6)

    # Multi-ine command
    total = r('''
        x <- c(1,2,3,4)
        sum(x)
    ''')
    eq_(total[0], 10)

    # Variables preserved across calls
    r('x <- c(5,4,3)')
    eq_(r('sum(x)')[0], 12)


def test_script():
    r(path='script1.R')
    eq_(r('first()')[0], 60)
    eq_(r('second()')[0], 100)


def test_args():
    r(path='script1.R')
    eq_(r('incr(n)', n=5)[0], 6)
    eq_(r(
        'mean(x, na.rm=narm, trim=trim)',
        x=pd.Series([0, 1, 2, 3, 4, 5, 6, None]),
        narm=True,
        trim=0.2,
    )[0], 3)
    cars = r('''
        data(cars)
        cars
    ''')
    ok_(isinstance(cars, pd.DataFrame))


def test_install():
    r('''
        packages <- c('rprojroot', 'ggplot2')
        new.packages <- packages[!(packages %in% installed.packages()[,"Package"])]
        if (length(new.packages)) install.packages(new.packages)
    ''')
    eq_(r(path='scriptpath.R')[0], os.path.join(folder, 'flags.csv').replace(os.sep, '/'))


def test_plots():
    path = r(path='scriptplot.R')
    img = Image.open(path[0])
    eq_(img.size, (512, 512))           # noqa: E912 Size matches
    freq = {color: count for count, color in img.convert('RGB').getcolors()}
    ok_(freq[255, 255, 255] < 50000)    # noqa: E912 Not filled with white
    ok_(freq[235, 235, 235] > 100000)   # noqa: E912 Mostly light grey
    ok_(freq[89, 89, 89] > 20000)       # noqa: E912 and some dark grey
