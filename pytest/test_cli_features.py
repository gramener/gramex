import os
import json
import pytest
import importlib.util

def get_test_directories():
    test_dirs = []
    for root, dirs, files in os.walk(os.getcwd()):
        if 'actual.py' in files and 'expected.json' in files:
            test_dirs.append(root)
    return test_dirs

@pytest.fixture(params=get_test_directories())
def actual_and_expected(request):
    root = request.param
    os.chdir(root)
    actual_path = os.path.join(root, 'actual.py')
    expected_path = os.path.join(root, 'expected.json')

    spec = importlib.util.spec_from_file_location("actual", actual_path)
    actual_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual_module)
    actual = actual_module.actual([], {})

    with open(expected_path, 'r') as expected:
        expected_result = json.load(expected)

    return actual, expected_result

def test_actual_vs_expected(actual_and_expected):
    actual, expected = actual_and_expected
    assert actual == expected
