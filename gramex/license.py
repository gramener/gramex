'''
This module implements different strategies to uniquely identify machines.

http://serialsense.com/blog/2011/02/generating-unique-machine-ids/
http://stackoverflow.com/questions/2461141/get-a-unique-computer-id-in-python-on-windows-and-linux

'''

import uuid


def mac_id():
    return uuid.getnode()


def cpu_id():
    raise NotImplementedError('CPU ID not yet implemented')


def bios_id():
    raise NotImplementedError('BIOS ID not yet implemented')
