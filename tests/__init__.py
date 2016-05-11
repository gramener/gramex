from . import server


def setUp():
    server.start_gramex()


def tearDown():
    server.stop_gramex()
