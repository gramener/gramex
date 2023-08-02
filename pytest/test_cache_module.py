import gramex.cache
import io
import json
import os
import pandas as pd
import pytest
import time
import yaml
from collections import OrderedDict
from markdown import markdown
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader
from pandas.testing import assert_frame_equal as afe
from utils import remove_if_possible
from tornado.template import Template

folder = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(folder, '..', 'testlib', 'test_cache')
tests_dir = os.path.join(folder, '..', 'tests')
small_delay = 0.01


def touch(path, times=None, data=None):
    with io.open(path, 'ab') as handle:
        os.utime(path, times)
        if data is not None:
            handle.write(data)


class TestOpen:
    @staticmethod
    def check_file_cache(path, check):
        check(reload=True)
        check(reload=False)
        touch(path)
        time.sleep(small_delay)
        check(reload=True)

    def test_rel(self):
        # Passing rel=True picks up the file from the current directory
        path = os.path.join(cache_dir, 'template.txt')
        with io.open(os.path.join(cache_dir, 'template.txt'), encoding='utf-8') as handle:
            expected = handle.read()
        assert gramex.cache.open(path, 'txt', rel=True) == expected

    def test_open_text(self):
        path = os.path.join(cache_dir, 'template.txt')
        expected = io.open(path, encoding='utf-8', errors='ignore').read()

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'text', _reload_status=True)
            assert reloaded == reload
            assert result == expected

        self.check_file_cache(path, check)
        assert gramex.cache.open(path) == gramex.cache.open(path, 'text')
        assert gramex.cache.open(path) == gramex.cache.open(path, 'txt')

    def test_open_bin(self):
        path = os.path.join(cache_dir, 'data.bin')
        expected = io.open(path, mode='rb').read()

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'bin', _reload_status=True)
            assert reloaded == reload
            assert result == expected

        self.check_file_cache(path, check)

    def test_open_csv(self):
        path = os.path.join(cache_dir, 'data.csv')
        expected = pd.read_csv(path, encoding='utf-8')

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'csv', _reload_status=True, encoding='utf-8'
            )
            assert reloaded == reload
            afe(result, expected)

        self.check_file_cache(path, check)
        afe(gramex.cache.open(path), gramex.cache.open(path, 'csv'))

    def test_open_json(self):
        path = os.path.join(cache_dir, 'data.json')
        with io.open(path, encoding='utf-8') as handle:
            expected = json.load(handle, object_pairs_hook=OrderedDict)

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'json', _reload_status=True, object_pairs_hook=OrderedDict
            )
            assert reloaded == reload
            assert isinstance(result, OrderedDict)
            assert result == expected

        self.check_file_cache(path, check)
        assert gramex.cache.open(path) == gramex.cache.open(path, 'json')

    def test_open_jsondata(self):
        path = os.path.join(cache_dir, 'data.jsondata')
        expected = pd.read_json(path)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'jsondata', _reload_status=True)
            assert reloaded == reload
            afe(result, expected)

        self.check_file_cache(path, check)
        afe(gramex.cache.open(path), gramex.cache.open(path, 'jsondata'))

    def test_xlsx(self):
        path = os.path.join(tests_dir, 'sales.xlsx')
        # Excel files are loaded via pd.read_excel by default
        afe(
            gramex.cache.open(path, sheet_name='sales'),
            pd.read_excel(path, sheet_name='sales', engine='openpyxl'),
        )
        # Load range. sales!A1:E25 is the same as the sheet "sales"
        afe(
            gramex.cache.open(path, sheet_name='sales', range='A1:E25'),
            pd.read_excel(path, sheet_name='sales', engine='openpyxl'),
        )
        # sheet_name defaults to 0
        afe(gramex.cache.open(path, range='A1:E25'), pd.read_excel(path, engine='openpyxl'))
        # sheet_name can be an int, not just a str
        afe(
            gramex.cache.open(path, sheet_name=1, range='A1:$B$34'),
            pd.read_excel(path, sheet_name=1, engine='openpyxl'),
        )
        # header can be any int or list of int, passed directly to pd.read_excel
        afe(
            gramex.cache.open(path, sheet_name='sales', header=[0, 1], range='A$1:$E25'),
            pd.read_excel(path, sheet_name='sales', header=[0, 1], engine='openpyxl'),
        )
        # header=None doesn't add a header
        afe(
            gramex.cache.open(path, sheet_name='sales', header=None, range='A$1:$E25'),
            pd.read_excel(path, sheet_name='sales', header=None, engine='openpyxl'),
        )
        # Load table. "SalesTable" is the same as table!A1B11
        afe(
            gramex.cache.open(path, sheet_name='table', table='SalesTable'),
            gramex.cache.open(path, sheet_name='table', range='A1:$B$11'),
        )
        afe(
            gramex.cache.open(path, sheet_name='table', table='CensusTable'),
            gramex.cache.open(path, sheet_name='table', range='$D1:F$23'),
        )
        # Load all links on table
        actual = gramex.cache.open(path, sheet_name='table', table='CensusTable', links=True)
        expected = gramex.cache.open(path, sheet_name='table', table='CensusTable')
        expected['District_link'] = 'https://example.org/' + expected['District']
        expected['DistrictCaps_link'] = 'https://example.org/' + expected['DistrictCaps'].head(2)
        afe(actual, expected)
        # Load explicit column links on range with multiple headers
        actual = gramex.cache.open(
            path,
            sheet_name='table',
            range='$D1:F$23',
            links={
                ('District', 'Kupwara'): 'DistrictLink',
                ('DistrictCaps', 'KUPWARA'): 'CapsLink',
            },
            header=[0, 1],
        )
        expected = gramex.cache.open(path, sheet_name='table', range='$D1:F$23', header=[0, 1])
        expected['DistrictLink'] = 'https://example.org/' + expected['District']
        expected['CapsLink'] = 'https://example.org/' + expected['DistrictCaps'].head(1)
        afe(actual, expected)
        # Load named range. The "sales" named range is the same as the sheet "sales"
        afe(
            gramex.cache.open(path, sheet_name='sales', name='sales'),
            gramex.cache.open(path, sheet_name='sales'),
        )
        # Load single column
        afe(
            gramex.cache.open(path, sheet_name='sales', range='B1:B5'),
            gramex.cache.open(path, sheet_name='sales')[['city']].head(4),
        )
        # Load single row
        afe(
            gramex.cache.open(path, sheet_name='sales', range='B1:E1', header=None),
            pd.DataFrame(gramex.cache.open(path, sheet_name='sales').columns[1:]).T,
        )
        # Load single cell
        afe(
            gramex.cache.open(path, sheet_name='sales', range='B1', header=None),
            pd.DataFrame([['city']]),
        )
        # TODO: Test failure conditions, edge cases, etc.

    def test_open_yaml(self):
        path = os.path.join(cache_dir, 'data.yaml')
        with io.open(path, encoding='utf-8') as handle:
            # B506:yaml_load is safe to use here since we're loading from a known safe file.
            # Specifically, we're testing whether Loader= is passed to gramex.cache.open.
            expected = yaml.load(handle, Loader=AttrDictYAMLLoader)  # nosec B506

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'yaml', _reload_status=True, Loader=AttrDictYAMLLoader
            )
            assert reloaded == reload
            assert isinstance(result, AttrDict)
            assert result == expected

        self.check_file_cache(path, check)
        assert gramex.cache.open(path) == gramex.cache.open(path, 'yaml')

    def test_open_template(self):
        path = os.path.join(cache_dir, 'template.txt')

        def check(reload):
            result, reloaded = gramex.cache.open(
                path, 'template', _reload_status=True, autoescape=None
            )
            assert reloaded == reload
            assert isinstance(result, Template)
            first_line = result.generate(name='高').decode('utf-8').split('\n')[0]
            assert first_line == '1: name=高'

        self.check_file_cache(path, check)

    def test_open_markdown(self):
        path = os.path.join(cache_dir, 'markdown.md')
        extensions = [
            'markdown.extensions.codehilite',
            'markdown.extensions.extra',
            'markdown.extensions.toc',
            'markdown.extensions.meta',
            'markdown.extensions.sane_lists',
            'markdown.extensions.smarty',
        ]
        with io.open(path, encoding='utf-8') as handle:
            expected = markdown(handle.read(), output_format='html5', extensions=extensions)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'md', _reload_status=True, encoding='utf-8')
            assert reloaded == reload
            assert isinstance(result, str)
            assert result == expected

        self.check_file_cache(path, check)
        assert gramex.cache.open(path) == gramex.cache.open(path, 'md')

    def test_open_custom(self):
        def img_size(path, scale=1):
            return tuple(v * scale for v in Image.open(path).size)

        def check(reload):
            result, reloaded = gramex.cache.open(path, 'png', _reload_status=True)
            assert reloaded == reload
            assert result == expected

        from PIL import Image

        path = os.path.join(cache_dir, 'data.png')
        expected = img_size(path)

        gramex.cache.open_callback['png'] = img_size
        self.check_file_cache(path, check)
        assert gramex.cache.open(path, scale=2) == tuple(v * 2 for v in expected)

    def test_save(self):
        path = os.path.join(cache_dir, 'data.csv')
        data = pd.read_csv(path, encoding='utf-8')
        config = {
            'html': {'index': False, 'escape': False, 'ignore_keyword': 1},
            'hdf': {'index': False, 'key': 'data', 'format': 'fixed', 'ignore_keyword': 1},
            'json': {'orient': 'records', 'ignore_keyword': 1},
            'csv': {'index': False, 'ignore_keyword': 1},
            'xlsx': {'index': False, 'sheet_name': 'Sheet1', 'ignore_keyword': 1},
            # 'stata': dict(index=False),   # cannot test since it doesn't support unicode
        }
        for ext, kwargs in config.items():
            target = os.path.join(cache_dir, 'killme.' + ext)
            gramex.cache.save(data, target, **kwargs)
            try:
                result = gramex.cache.open(target)
                if ext == 'html':
                    result = result[0]
                elif ext == 'json':
                    result = pd.DataFrame(data)
                afe(result, data)
            finally:
                remove_if_possible(target)

    def test_custom_cache(self):
        path = os.path.join(cache_dir, 'data.csv')
        cache = {}
        kwargs = {'_reload_status': True, '_cache': cache}
        result, reloaded = gramex.cache.open(path, 'csv', **kwargs)
        cache_key = (path, 'csv', gramex.cache.hashfn(None), frozenset())
        assert cache_key in cache

        # Initially, the file is loaded
        assert reloaded is True

        # Next time, it's loaded from the cache
        result, reloaded = gramex.cache.open(path, 'csv', **kwargs)
        assert reloaded is False

        # If the cache is deleted, it reloads
        del cache[cache_key]
        result, reloaded = gramex.cache.open(path, 'csv', **kwargs)
        assert reloaded is True

        # Additional kwargs are part of the cache key
        result, reloaded = gramex.cache.open(path, encoding='utf-8', **kwargs)
        cache_key = (path, None, gramex.cache.hashfn(None), frozenset([('encoding', 'utf-8')]))
        assert cache_key in cache
        assert reloaded is True
        result, reloaded = gramex.cache.open(path, encoding='utf-8', **kwargs)
        assert reloaded is False

        # Changing the kwargs reloads the data
        result, reloaded = gramex.cache.open(path, encoding='cp1252', **kwargs)
        assert reloaded is True
        result, reloaded = gramex.cache.open(path, encoding='cp1252', **kwargs)
        assert reloaded is False

        # Cache is not fazed by non-hashable inputs.
        result, reloaded = gramex.cache.open(
            path,
            header=0,
            parse_dates={'date': [0, 1, 2]},
            dtype={'a': int, 'b': float, 'c': int},
            **kwargs,
        )
        cache_key = (
            path,
            None,
            gramex.cache.hashfn(None),
            frozenset(
                [
                    ('header', 0),  # hashable values hashed as-is
                    ('parse_dates', '[{"date":[0,1,2]}]'),  # converts to compact json if possible
                    ('dtype', None),  # gives up with None otherwise
                ]
            ),
        )
        assert cache_key in cache

    def test_change_cache(self):
        path = os.path.join(cache_dir, 'data.csv')
        new_cache = {}
        old_cache = gramex.cache._OPEN_CACHE
        cache_key = (path, 'csv', gramex.cache.hashfn(None), frozenset())

        # Ensure that the path is cached
        gramex.cache.open(path, 'csv')
        assert cache_key in old_cache

        # Updating the cache copies data and empties from the old one
        new_cache.update(old_cache)
        gramex.cache._OPEN_CACHE = new_cache
        old_cache.clear()

        # New requests are cached in the new cache
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True)
        assert reloaded is False
        assert cache_key in new_cache
        del new_cache[cache_key]
        old_cache.pop(cache_key, None)
        assert cache_key not in new_cache
        result, reloaded = gramex.cache.open(path, 'csv', _reload_status=True)
        assert reloaded is True
        assert cache_key in new_cache
        assert cache_key not in old_cache

    def test_multiple_loaders(self):
        # Loading the same file via different callbacks should return different results
        path = os.path.join(cache_dir, 'multiformat.csv')
        data = gramex.cache.open(path, 'csv')
        assert isinstance(data, pd.DataFrame)
        text = gramex.cache.open(path, 'text')
        assert isinstance(text, str)
        none = gramex.cache.open(path, lambda path: None)
        assert none is None

    def test_invalid_callbacks(self):
        path = os.path.join(cache_dir, 'multiformat.csv')
        with pytest.raises(TypeError):
            gramex.cache.open(path, 'nonexistent')
        with pytest.raises(TypeError):
            gramex.cache.open(path, 1)
        with pytest.raises(TypeError):
            gramex.cache.open('invalid.ext')

    def test_stat(self):
        path = os.path.join(cache_dir, 'multiformat.csv')
        stat = os.stat(path)
        assert gramex.cache.stat(path) == (stat.st_mtime, stat.st_size)
        assert gramex.cache.stat('nonexistent') == (None, None)

    def test_transform(self):
        # Check that transform function is applied and used as a cache key
        cache = {}
        path = os.path.join(cache_dir, 'data.csv')

        data = gramex.cache.open(path, 'csv', transform=len, _cache=cache)
        assert data == len(pd.read_csv(path))
        cache_key = (path, 'csv', gramex.cache.hashfn(len), frozenset([]))
        assert cache_key in cache

        def transform2(d):
            return d['a'].sum()

        data = gramex.cache.open(path, 'csv', transform=transform2, _cache=cache)
        assert data == pd.read_csv(path)['a'].sum()
        cache_key = (path, 'csv', gramex.cache.hashfn(transform2), frozenset([]))
        assert cache_key in cache

        # Check that non-callable transforms are ignored but used as cache key
        data = gramex.cache.open(path, 'csv', transform='ignore', _cache=cache)
        afe(data, pd.read_csv(path))
        cache_key = (path, 'csv', gramex.cache.hashfn('ignore'), frozenset([]))
        assert cache_key in cache

        # Check that temporary caches are hashed by function
        v = 1
        data = gramex.cache.open(path, 'csv', lambda x: v, _cache=cache)
        assert data == 1
        v = 2
        data = gramex.cache.open(path, 'csv', lambda x: v, _cache=cache)
        assert data == 2
