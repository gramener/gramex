These are the main test cases for Gramex. Running any test will start Gramex in a
new thread (the `setUp()` function in `__init__.py` calls
`server.start_gramex()`.)

Running tests
-------------

Use `python setup.py nosetests`, or just `nosetests`.

You can run specific tests. For example, this only runs `test_auth.py` and `test_cache.py`:

    nosetests tests.test_auth tests.test_cache

This only runs the class `TestLDAPAuth` in `test_auth.py`:

    nosetests tests.test_auth:TestLDAPAuth
