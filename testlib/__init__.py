import os
import sys

# dbutils.py is in ../tests/ -- import it. (This is a not elegant.)
folder = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.normpath(os.path.join(folder, '..', 'tests'))
sys.path.append(tests_dir)
