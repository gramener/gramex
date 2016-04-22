import os
import sys


def main():
    'Print cwd and sys.argv'
    sys.stderr.write('stderr starts\n')
    sys.stdout.write('stdout starts\n')
    sys.stdout.write('os.getcwd: %s\n' % os.path.abspath(os.getcwd()))
    for index, arg in enumerate(sys.argv):
        sys.stdout.write('sys.argv[%d]: %s\n' % (index, arg))
    sys.stderr.write('stderr ends\n')
    sys.stdout.write('stdout ends\n')


if __name__ == '__main__':
    main()
