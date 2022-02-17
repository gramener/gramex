import os
import sys
import logging
from pandas.testing import assert_frame_equal as afe   # noqa: F401 - other modules use this
from pandas.testing import assert_series_equal as ase  # noqa: F401 - other modules use this

# Import from ../tests/ folder. e.g. dbutils.py for use in test_data.py, etc.
# This is a not elegant.
folder = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.normpath(os.path.join(folder, '..', 'tests'))
sys.path.append(tests_dir)
import dbutils                          # noqa
from tests import remove_if_possible    # noqa

# Location of the sales data file
sales_file = os.path.join(tests_dir, 'sales.xlsx')

# Turn off matplotlib's verbose debug logging
mpl_logger = logging.getLogger('matplotlib')
mpl_logger.setLevel(logging.WARNING)
