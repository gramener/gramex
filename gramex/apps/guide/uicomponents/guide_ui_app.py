"""Data processing functionalities."""
from __future__ import unicode_literals

import os
import json
import gramex.cache


folder = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(folder, 'config.yaml')


def get_config(handler):
    '''Return config.yaml as a JSON file'''
    config = gramex.cache.open(config_file, 'config')
    return json.dumps(config, ensure_ascii=True, indent=2)
