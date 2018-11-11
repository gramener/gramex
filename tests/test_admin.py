from . import TestGramex


class TestAdmin(TestGramex):
    def test_default(self):
        r = self.check('/admin/default/')
        self.check_css(
            r.text,
            ('title', 'Admin'),
            ('link', {'href': 'ui/bootstraptheme.css'}),
            ('h3', 'has', 'Users'),
            ('h3', 'has', 'Shell'),
            ('h3', 'has', 'Info'),
            ('h3', 'has', 'Config'),
            ('h3', 'has', 'Logs'),
        )

    def test_kwargs(self):
        r = self.check('/admin/kwargs/')
        self.check_css(
            r.text,
            ('title', 'Custom title'),
            ('link', {'href': 'ui/bootstraptheme.css?font-family-base=roboto'}),
            ('.navbar-brand img', {'src': 'logo.png'}),
            ('h3', 'has', 'Users'),
            ('h3', 'has', 'Shell'),
            ('h3', 'has', 'Info'),
        )

    def test_info(self):
        self.check('/admin/default/?tab=info')
        # TODO: add tests

    def test_users(self):
        self.check('/admin/default/?tab=users')
        # TODO: add tests

    def test_shell(self):
        self.check('/admin/default/?tab=shell')
        # TODO: add tests
