import gramex.cache
import os
import pytest
from glob import glob
from pandas.testing import assert_frame_equal
from gramex.install import features
from gramex.install import complexity
from pandas import read_json

folder = os.path.dirname(os.path.abspath(__file__))


def test_features_empty():
    assert features(['/nonexistent'], {}) == ''


@pytest.mark.parametrize("root", glob(os.path.join(folder, 'features_*')))
def test_features(root):
    actual = features([root], {'format': 'csv'})
    expected = gramex.cache.open(os.path.join(root, 'expected.csv'), 'text')
    assert expected == actual


@pytest.mark.parametrize("root", glob(os.path.join(folder, 'complexity_*')))
def test_complexity(root):
    actual = complexity([root], {})
    expected = read_json(os.path.join(root, 'expected.json'))
    assert_frame_equal(expected, actual)
