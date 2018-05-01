import os.path
import gramex.cache

folder = os.path.dirname(os.path.abspath(__file__))
path = os.path.normpath(os.path.join(folder, 'examples.yaml'))
examples = gramex.cache.open(path, 'yaml')
