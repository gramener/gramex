# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import unittest
import datetime
import dateutil
import pandas as pd
from orderedattrdict import AttrDict
from gramex.config import CustomJSONEncoder, CustomJSONDecoder
from nose.tools import eq_


localtz = dateutil.tz.tzlocal()


class TestJSON(unittest.TestCase):

    def test_encoder(self):
        # Naive date is converted into a tz aware date
        date = datetime.datetime.now()
        tz_date = date.replace(tzinfo=localtz)
        eq_(json.dumps(date, cls=CustomJSONEncoder), '"%s"' % tz_date.isoformat())

        # TZ aware date is retained as-is
        date = datetime.datetime.now(tz=localtz)
        eq_(json.dumps(date, cls=CustomJSONEncoder), '"%s"' % date.isoformat())

        # Date is converted in a deep hierarchy
        data = {'str': 'x', 'bool': True, 'num': 1, 'date': date}
        result = {'str': 'x', 'bool': True, 'num': 1, 'date': date.isoformat()}
        eq_(
            json.dumps(data, cls=CustomJSONEncoder),
            json.dumps(result))

        df1 = [{'x': 1.0, 'y': 'σ'}, {'x': None, 'y': None}, {'x': 0.0, 'y': '►'}]
        result = {'x': df1}
        eq_(
            json.dumps({'x': pd.DataFrame(df1)}, cls=CustomJSONEncoder, sort_keys=True),
            json.dumps(result, sort_keys=True))

        # numpy types are converted to python standard types
        data = {'x': pd.np.arange(1), 'y': pd.np.int64(1), 'z': pd.np.float32(1)}
        result = {'x': [0], 'y': 1, 'z': 1.0}
        eq_(
            json.dumps(data, cls=CustomJSONEncoder, sort_keys=True),
            json.dumps(result, sort_keys=True))

    def test_decoder(self):
        date = datetime.datetime(year=2001, month=2, day=3, hour=4, minute=5, second=6,
                                 microsecond=0, tzinfo=dateutil.tz.tzutc())
        datestr = '"2001-02-03T04:05:06+0000"'
        eq_(json.loads(datestr, cls=CustomJSONDecoder), date)

        datestr = '"2001-02-03T04:05:06Z"'
        eq_(json.loads(datestr, cls=CustomJSONDecoder), date)

        datestr = '"2001-02-03T04:05:06.000+0000"'
        eq_(json.loads(datestr, cls=CustomJSONDecoder), date)

        datestr = '"2001-02-03T04:05:06.000Z"'
        eq_(json.loads(datestr, cls=CustomJSONDecoder), date)

        data = '{"x": 1, "y": "2001-02-03T04:05:06.000Z"}'
        eq_(json.loads(data, cls=CustomJSONDecoder), {
            'x': 1,
            'y': date
        })
        eq_(json.loads(data, cls=CustomJSONDecoder, object_pairs_hook=AttrDict),
            AttrDict([('x', 1), ('y', date)]))

    def check_roundtrip(self, val):
        encoded = json.dumps(val, cls=CustomJSONEncoder)
        decoded = json.loads(encoded, cls=CustomJSONDecoder)
        eq_(decoded, val)

        encoded = json.dumps(val, cls=CustomJSONEncoder)
        decoded = json.loads(encoded, cls=CustomJSONDecoder, object_pairs_hook=AttrDict)
        eq_(decoded, val)

    def test_roundtrip(self):
        date = datetime.datetime.now()
        tz_date = date.replace(tzinfo=localtz)

        self.check_roundtrip(tz_date)
        self.check_roundtrip(AttrDict([
            ('str', 'x'), ('bool', True), ('num', 1), ('date', tz_date)]))
