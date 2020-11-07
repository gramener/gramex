'''
Utilities to test gramex.transforms.handler
'''

import datetime
import gramex.cache
import json
import numpy as np
from typing import List
from gramex.transforms import handler


@handler
def yielder(*i):
    for item in i:
        yield item


@handler
def power(x: int, y: float) -> float:
    return y ** x


@handler
def total(*items: float) -> float:
    return sum(items)


@handler
def multilist(items: List[int], start: float) -> float:
    return sum(items, start)


@handler
def strtotal(*items: str) -> str:
    s = ''
    for i in items:
        s += i
    return s


@handler
def name_age(name, age):
    return f'{name} is {age} years old.'


@handler
def hints(name: str, age: int) -> str:
    return f'{name} is {age} years old.'


@handler
def nativetypes(a: int, b: float, c: bool, d: str, e: None, f: np.uintc, g: np.double, h: np.str_,
                i: np.bool8):
    '''Yield objects of almost all types, plus list and dict'''
    yield a
    yield b
    yield c
    yield d
    yield e
    yield f
    yield g
    yield h
    yield i
    yield datetime.datetime(year=2020, month=1, day=1, tzinfo=datetime.timezone.utc)
    yield {'a': a, 'b': b}
    yield [a, b]


@handler
def greet(name="Stranger"):
    return f'Hello, {name}!'


@handler
def sales():
    return gramex.cache.open('sales.xlsx', rel=True)


@handler
def content(x: int, y: str, handler):
    if y == 'json':
        handler.set_header('Content-Type', 'application/json')
        return json.dumps({'x': x}, separators=(',', ':'))
    elif y == 'txt':
        handler.set_header('Content-Type', 'text/plain')
        return f'x={x}'
