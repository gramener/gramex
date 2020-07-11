import os
import inspect
import unittest
import gramex


class TestSetup(unittest.TestCase):
    # Ensure pip install has the right set of files
    src_dir = os.path.dirname(inspect.getfile(gramex))

    def exists(self, path):
        self.assertTrue(os.path.exists(os.path.join(self.src_dir, path)),
                        'Missing %s' % path)

    def test_setup(self):
        # List all files mentioned in setup.py - package_data: key
        self.exists('gramex.yaml')
        self.exists('deploy.yaml')
        self.exists('apps.yaml')
        self.exists('favicon.ico')
        self.exists('release.json')

        # Ensure that handler HTML files are there by checking for all files
        self.exists('handlers/filehandler.template.html')
        self.exists('handlers/auth.template.html')
        self.exists('handlers/auth.recaptcha.template.html')

        # Ensure that all JSON files in pptgen/ are included
        self.exists('pptgen/fonts.json')
        self.exists('pptgen/colors.json')
        self.exists('pptgen/release.json')

        # Ensure that all YAML files in pptgen2/ are included
        self.exists('pptgen2/config.yaml')
