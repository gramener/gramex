from . import TestGramex


class TestSubApp(TestGramex):
    # Test applications imported from subdirectories

    def test_subapp(self):
        self.check('/subapp/', text='OK')
