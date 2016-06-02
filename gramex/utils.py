from .config import app_log


class _Utils(object):
    ssl_checked = False

    @classmethod
    def check_old_certs(cls):
        '''
        The latest SSL certificates from certifi don't work for Google Auth. Do
        a one-time check to access accounts.google.com. If it throws an SSL
        error, switch to old SSL certificates. See
        https://github.com/tornadoweb/tornado/issues/1534
        '''
        if not cls.ssl_checked:
            import ssl
            from tornado.httpclient import HTTPClient, AsyncHTTPClient

            # Use HTTPClient to check instead of AsyncHTTPClient because it's synchronous.
            _client = HTTPClient()
            try:
                # Use accounts.google.com because we know it fails with new certifi certificates
                # cdn.redhat.com is another site that fails.
                _client.fetch("https://accounts.google.com/")
            except ssl.SSLError:
                try:
                    import certifi      # noqa: late import to minimise dependencies
                    AsyncHTTPClient.configure(None, defaults=dict(ca_certs=certifi.old_where()))
                    app_log.warn('Using old SSL certificates for compatibility')
                except ImportError:
                    pass
            except Exception:
                # Ignore any other kind of exception
                app_log.warn('Gramex has no direct Internet connection.')
            _client.close()
            cls.ssl_checked = True


check_old_certs = _Utils.check_old_certs
