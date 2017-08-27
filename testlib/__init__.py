import os
import sys

# Allow importing modules from ../tests/
# For example, ../tests/dbutils.py us used by test_data.py
# This is a not elegant.
folder = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.normpath(os.path.join(folder, '..', 'tests'))
sys.path.append(tests_dir)

# Location of the sales data file
sales_file = os.path.join(tests_dir, 'sales.xlsx')
