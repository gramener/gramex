import os
import json
import glob
from gramex.install import complexity


def test_cli_features():
    for root in glob.glob('pytest/complexity-*'):    
        path = os.path.join(os.getcwd(), root)
        actual = complexity([path], {})
        expected_path = os.path.join(path, 'expected.json')

        with open(expected_path, 'r') as expected:
            expected = json.load(expected)
            assert expected == actual
