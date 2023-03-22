import os
import glob
from pandas import read_json
from pandas.testing import assert_frame_equal
from gramex.install import features


def test_cli_features():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    getGlob = lambda x: glob.glob(os.path.join(dir_path, f'{x}-*'))
    for root in getGlob('complexity') +  getGlob('features'):
        actual = features([root], {})
        expected = read_json(os.path.join(root, 'expected.json'))
        assert_frame_equal( expected, actual)
