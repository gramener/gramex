import gramex.cache
import os
import pytest
from glob import glob
from pandas.testing import assert_frame_equal
from gramex.install import features
from gramex.install import complexity
from pandas import read_json


folder = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="function", autouse=True)
def create_test_files(request):
    files2create = {
        (
            "complexity_basic",
            "site-packages",
            "lorem.py",
        ): '''
        """
        Complexity O(m*n)
        This file will be ignored in calculation being inside "site-packages"
        """


        def lcs(x, y):
            m = len(x)
            n = len(y)
            lcs = [[0] * (n + 1) for i in range(m + 1)]
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if x[i - 1] == y[j - 1]:
                        lcs[i][j] = lcs[i - 1][j - 1] + 1
                    else:
                        lcs[i][j] = max(lcs[i - 1][j], lcs[i][j - 1])
            return lcs[m][n]
        ''',
        (
            "complexity_basic",
            "node_modules",
            "ipsum.py",
        ): '''

        """
        Complexity: O(n log n) in worst case
        This file will be ignored in calculation being inside "node_modules"
        """


        def merge_sort(arr):
            if len(arr) <= 1:
                return arr
            mid = len(arr) // 2
            left = merge_sort(arr[:mid])
            right = merge_sort(arr[mid:])
            return merge(left, right)


        def merge(left, right):
            result = []
            i, j = 0, 0
            while i < len(left) and j < len(right):
                if left[i] <= right[j]:
                    result.append(left[i])
                    i += 1
                else:
                    result.append(right[j])
                    j += 1
            result += left[i:]
            result += right[j:]
            return result
        ''',
        (
            "complexity_basic",
            "subfolder",
            "js-default",
            "site-packages",
            "add.js",
        ): """
        function add(a, b) {
            return a + b;
        }
        """,
    }
    files = []
    for filetpl, content in files2create.items():
        filepath = os.path.join(folder, *filetpl)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        files.append(filepath)
        with open(filepath, "w") as f:
            f.write(content)

    def remove_test_files():
        for filepath in files:
            os.remove(filepath)

    request.addfinalizer(remove_test_files)


def test_features_empty():
    assert features(["/nonexistent"], {}) == ""


@pytest.mark.parametrize("root", glob(os.path.join(folder, "features_*")))
def test_features(root):
    actual = features([root], {"format": "csv"})
    expected = gramex.cache.open(os.path.join(root, "expected.csv"), "text")
    assert expected == actual


@pytest.mark.parametrize("root", glob(os.path.join(folder, "complexity_*")))
def test_complexity(root):
    actual = complexity([root], {})
    expected = read_json(os.path.join(root, "expected.json"))
    # NOTE: This test will fail when Gramex code complexity changes.
    # Update complexity_*/expected.json with the actual value and re-run.
    assert_frame_equal(expected, actual)
