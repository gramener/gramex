import json
import datetime
import dateutil
import numpy as np
import pandas as pd
from orderedattrdict import AttrDict
from gramex.config import CustomJSONEncoder, CustomJSONDecoder


localtz = dateutil.tz.tzlocal()


def test_encoder():
    # Naive date is converted into a tz aware date
    date = datetime.datetime.now()
    tz_date = date.replace(tzinfo=localtz)
    assert json.dumps(date, cls=CustomJSONEncoder) == '"%s"' % tz_date.isoformat()

    # TZ aware date is retained as-is
    date = datetime.datetime.now(tz=localtz)
    assert json.dumps(date, cls=CustomJSONEncoder) == '"%s"' % date.isoformat()

    # Date is converted in a deep hierarchy
    data = {'str': 'x', 'bool': True, 'num': 1, 'date': date}
    result = {'str': 'x', 'bool': True, 'num': 1, 'date': date.isoformat()}
    assert json.dumps(data, cls=CustomJSONEncoder) == json.dumps(result)

    # Unicode is converted propertly
    df1 = [{'x': 1.0, 'y': 'σ'}, {'x': None, 'y': None}, {'x': 0.0, 'y': '►'}]
    result = {'x': df1}
    assert json.dumps({'x': pd.DataFrame(df1)}, cls=CustomJSONEncoder) == json.dumps(result)

    # numpy types are converted to python standard types
    data = {'x': np.arange(1), 'y': np.int64(1), 'z': np.float32(1), 'a': np.bool_(True)}
    result = {'x': [0], 'y': 1, 'z': 1.0, 'a': True}
    assert json.dumps(data, cls=CustomJSONEncoder) == json.dumps(result)

    # Pandas Series is converted to an object
    data = {'x': pd.Series([1, 2, 3]), 'y': pd.Series({'a': 1, 'b': 2})}
    result = {'x': {0: 1, 1: 2, 2: 3}, 'y': {'a': 1, 'b': 2}}
    assert json.dumps(data, cls=CustomJSONEncoder) == json.dumps(result)

    # Pandas DataFrame is converted to an array of objects
    data = {'x': pd.DataFrame({'a': [1, 2, None], 'b': [4, 5, 6]})}
    result = {'x': [{'a': 1.0, 'b': 4}, {'a': 2.0, 'b': 5}, {'a': None, 'b': 6}]}
    assert json.dumps(data, cls=CustomJSONEncoder) == json.dumps(result)


def test_decoder():
    date = datetime.datetime(
        year=2001,
        month=2,
        day=3,
        hour=4,
        minute=5,
        second=6,
        microsecond=0,
        tzinfo=dateutil.tz.tzutc(),
    )
    datestr = '"2001-02-03T04:05:06+0000"'
    assert json.loads(datestr, cls=CustomJSONDecoder) == date

    datestr = '"2001-02-03T04:05:06Z"'
    assert json.loads(datestr, cls=CustomJSONDecoder) == date

    datestr = '"2001-02-03T04:05:06.000+0000"'
    assert json.loads(datestr, cls=CustomJSONDecoder) == date

    datestr = '"2001-02-03T04:05:06.000Z"'
    assert json.loads(datestr, cls=CustomJSONDecoder) == date

    data = '{"x": 1, "y": "2001-02-03T04:05:06.000Z"}'
    assert json.loads(data, cls=CustomJSONDecoder) == {'x': 1, 'y': date}
    assert json.loads(data, cls=CustomJSONDecoder, object_pairs_hook=AttrDict) == AttrDict(
        [('x', 1), ('y', date)]
    )


def check_roundtrip(val):
    encoded = json.dumps(val, cls=CustomJSONEncoder)
    decoded = json.loads(encoded, cls=CustomJSONDecoder)
    assert decoded == val

    encoded = json.dumps(val, cls=CustomJSONEncoder)
    decoded = json.loads(encoded, cls=CustomJSONDecoder, object_pairs_hook=AttrDict)
    assert decoded == val


def test_roundtrip():
    date = datetime.datetime.now()
    tz_date = date.replace(tzinfo=localtz)

    check_roundtrip(tz_date)
    check_roundtrip(AttrDict([('str', 'x'), ('bool', True), ('num', 1), ('date', tz_date)]))
