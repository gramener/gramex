import os
import pytest
import json
import importlib.util


for root, dirs, files in os.walk(os.getcwd()):
    if 'actual.py' not in files:
        continue
    os.chdir(root)
    actual_path = os.path.join(root, 'actual.py')
    expected_path = os.path.join(root, 'expected.json')
    spec = importlib.util.spec_from_file_location("actual", actual_path)
    actual_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual_module)
    actual = actual_module.actual([], {})

    with open(expected_path, 'r') as expected:
        assert actual == json.load(expected)

