'''
Utilities to test gramex.transforms.handler
'''

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
def nativetypes(a: int, b: float, c: bool, d: str, e: None):
    return {'msg': f'{a}*{b}={a * b}.', 'c': c, 'd': d, 'e': e}


@handler
def greet(name="Stranger"):
    return f'Hello, {name}!'
