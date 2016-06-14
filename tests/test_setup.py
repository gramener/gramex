import os
import inspect
import unittest
import gramex


class TestSetup(unittest.TestCase):
    'Ensure pip install has the right set of files'
    src_dir = os.path.dirname(inspect.getfile(gramex))

    def exists(self, path):
        self.assertTrue(os.path.exists(os.path.join(self.src_dir, path)),
                        'Missing %s' % path)

    def test_setup(self):
        self.exists('handlers/filehandler.template.html')
        self.exists('apps/guide/index.html')
        self.exists('apps/guide/gramex.yaml')
        self.exists('apps/guide/README.md')
        self.exists('apps/guide/install/README.md')
