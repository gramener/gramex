import gramex.cache
import os
import pytest
from glob import glob
from pandas.testing import assert_frame_equal
from gramex.install import features

folder = os.path.dirname(os.path.abspath(__file__))


def test_empty():
    assert features(['/nonexistent'], {}) is None


@pytest.mark.parametrize("root", glob(os.path.join(folder, 'features-*')))
def test_folders(root):
    actual = features([root], {})
    expected = gramex.cache.open(os.path.join(root, 'expected.csv'))
    assert_frame_equal(expected, actual)
