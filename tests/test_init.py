from __future__ import unicode_literals

import gramex
from orderedattrdict import AttrDict
from . import TestGramex


class TestInit(TestGramex):
    def test_init(self):
        self.check('/init/new', code=404)
        gramex.init(
            app=AttrDict(
                url=AttrDict(
                    init_new=AttrDict(
                        pattern='/init/new',
                        handler='FunctionHandler',
                        kwargs=AttrDict(
                            function='json.dumps({"key": "val1"})'
                        )
                    )
                )
            )
        )
        self.check('/init/new', text='{"key": "val1"}')
        gramex.init(
            app=AttrDict(
                url=AttrDict(
                    init_new=AttrDict(
                        pattern='/init/new',
                        handler='FunctionHandler',
                        kwargs=AttrDict(
                            function='json.dumps({"key": "val2"})'
                        )
                    )
                )
            )
        )
        self.check('/init/new', text='{"key": "val2"}')

    def test_reload(self):
        def re_init():
            gramex.init(
                app=AttrDict(
                    url=AttrDict(
                        init_reload=AttrDict(
                            pattern='/init/reload',
                            handler='utils.CounterHandler'
                        )
                    )
                )
            )

        re_init()
        self.check('/init/reload', text='1')
        re_init()
        self.check('/init/reload', text='1')
