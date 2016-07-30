import unittest
from gramex import parse_command_line


class TestParse(unittest.TestCase):
    def test_parse(self):
        def eq(cmd, value):
            value.setdefault('_', [])
            return self.assertEqual(parse_command_line(cmd), value)

        # Positional arguments
        eq([], {})
        eq(['x'], {'_': ['x']})
        eq(['x', 'y'], {'_': ['x', 'y']})

        # Single optional argument
        eq(['-x'], {'x': True})
        eq(['--x'], {'x': True})
        # First true gets eaten up
        eq(['-x=true'], {'x': True})
        eq(['-x=true', 'x'], {'x': 'x'})
        eq(['-x', 'true', 'x'], {'x': 'x'})
        # subsequent true values do not get eaten up
        eq(['-x', 'x', 'true'], {'x': ['x', True]})

        # Single arguments with values
        eq(['-x=1'], {'x': 1})
        eq(['--x=x'], {'x': 'x'})
        eq(['-x', '1'], {'x': 1})
        eq(['-x', '1', '2', 'x'], {'x': [1, 2, 'x']})

        # Multiple optional values
        eq(['-x=1', '--y=2'], {'x': 1, 'y': 2})
        eq(['-x', '1', '--y', '2'], {'x': 1, 'y': 2})

        # Positional + optional arguments
        eq(['x', '-x=1', 'x', '--y=2', '-z'], {'_': ['x'], 'x': [1, 'x'], 'y': 2, 'z': True})

        # Key breakup
        eq(['-p.q=1'], {'p': {'q': 1}})
        eq(['--p.q.r'], {'p': {'q': {'r': True}}})
        eq(['--p.q.r', 'x'], {'p': {'q': {'r': 'x'}}})
        eq(['--p.q.r', 'x', 'y'], {'p': {'q': {'r': ['x', 'y']}}})
        eq(['-p.q=1', '-p.r'], {'p': {'q': 1, 'r': True}})
        eq(['-p.q=1', '-p.r=2'], {'p': {'q': 1, 'r': 2}})
