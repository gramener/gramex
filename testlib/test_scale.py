import unittest
from gramex.scale import color
from nose.tools import eq_
from numpy.testing import assert_array_equal as aeq


class TestColor(unittest.TestCase):
    def test_default(self):
        c = color([0, 1], ['black', 'white'])
        eq_(c(0), '#000000')
        eq_(c(0.25), '#404040')
        eq_(c(0.5), '#808080')
        eq_(c(0.75), '#c0c0c0')
        eq_(c(1), '#ffffff')
        aeq(c([-1000, +1000]), ['#000000', '#ffffff'])

    def test_domain(self):
        # Map from -100 (black) to +100 (white)
        c = color([-100, +100], ['black', 'white'])
        eq_(c(0), '#808080')
        aeq(c([-100, -50, 0, 50, 100]), ['#000000', '#404040', '#808080', '#c0c0c0', '#ffffff'])
        aeq(c([-1000, +1000]), ['#000000', '#ffffff'])

        # Can't have just 1 value in the domain
        with self.assertRaises(ValueError):
            c = color([0], ['#ccc'])
        # Can't have just 1 value in the range
        with self.assertRaises(ValueError):
            c = color([0, 1, 2], ['#ccc'])

        # When len(domain) > len(range), range must haev exactly 2 values
        c = color([-100, 1, 2, 3, 100], ['black', 'white'])
        aeq(c([-100, -50, 0, 50, 100]), ['#000000', '#404040', '#808080', '#c0c0c0', '#ffffff'])
        with self.assertRaises(ValueError):
            c = color([-100, 1, 2, 3, 100], ['black', '#111', 'white'])

    def test_piecewise(self):
        # Maps piecewise linearly
        c = color([-100, 0, +100], ['black', '#c0c0c0', 'white'])
        eq_(c(-50), '#606060')
        aeq(c([-100, -50, 0, 50, 100]), ['#000000', '#606060', '#c0c0c0', '#e0e0e0', '#ffffff'])
        aeq(c([-1000, +1000]), ['#000000', '#ffffff'])

        c = color([0, 1, 2, 3], ['black', '#3f3f3f', '#c0c0c0', 'white'])
        aeq(c([0, 0.5, 1, 1.5, 2, 2.5, 3]),
            ['#000000', '#1f1f1f', '#3f3f3f', '#808080', '#c0c0c0', '#e0e0e0', '#ffffff'])
        aeq(c([-1000, +1000]), ['#000000', '#ffffff'])

    def test_bin(self):
        # Maps into buckets
        c = color([-1, 0, +1], ['black', 'white'], bin=True)
        aeq(c([-1, -0.5, 0, 0.5, 1.0]), ['#000000', '#000000', '#ffffff', '#ffffff', '#ffffff'])
        aeq(c([-1000, +1000]), ['#000000', '#ffffff'])

        c = color([-2, -1, 0, +1, +2], ['black', '#111', '#eee', 'white'], bin=True)
        aeq(c([-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2]), [
            '#000000', '#000000', '#111111', '#111111',
            '#eeeeee', '#eeeeee', '#ffffff', '#ffffff', '#ffffff'])
        aeq(c([-1000, +1000]), ['#000000', '#ffffff'])

        # But len(range) must be 1 less than len(domain)
        with self.assertRaises(ValueError):
            color([-2, -1, 0, +1, +2], ['black', '#111'], bin=True)

    def test_colormap(self):
        c = color([-1, 0, 1], 'RdYlGn')
        aeq(c([-1, -0.5, 0, 0.5, 1]), ['#a50026', '#f98e52', '#feffbe', '#84ca66', '#006837'])
        aeq(c([-1000, +1000]), ['#a50026', '#006837'])

        c = color([-1, 0, 1], 'RdYlGn', bin=True)
        aeq(c([-1, -0.5, 0, 0.5, 1]), ['#a50026', '#a50026', '#006837', '#006837', '#006837'])

        c = color([-1, -0.5, 0, 0.5, 1], 'RdYlGn', bin=True)
        aeq(c([-1, -0.8, -0.5, -0.2, 0, 0.2, 0.5, 0.8, 1]), [
            '#a50026', '#a50026', '#fdbf6f', '#fdbf6f',
            '#b7e075', '#b7e075', '#006837', '#006837', '#006837'
        ])
        # Test valid and invalid color maps
        for cm in ['viridis', 'plasma', 'Blues', 'RdYlGn', 'PuBuGn', 'Pastel1', 'twilight']:
            color([-1, 0, 1], cm)
        with self.assertRaises(ValueError):
            color([-1, 0, 1], 'invalid')
