# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import unittest
from gramex.services import encrypt
from nose.tools import eq_
from . import folder


class TestEncrypt(unittest.TestCase):
    encrypter = encrypt({
        'public_key': os.path.join(folder, 'id_rsa.pub'),
        'private_key': os.path.join(folder, 'id_rsa'),
    })
    items = [
        True, False,
        'string', '高兴',
        0, 1.5,
        {'高兴': '高兴'}, ['高兴', 2.4, True, None],
        {'高兴': ['高兴', 0, {'key': False}]},
    ]

    def test_encrypt(self):
        for src in self.items:
            encrypted = self.encrypter.encrypt(src)
            decrypted = self.encrypter.decrypt(encrypted)
            eq_(src, decrypted)
