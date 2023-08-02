import sys
import time


def write(n):
    sys.stdout.write('OUT:%d\n' % n)
    sys.stderr.write('ERR:%d\n' % n)
    sys.stdout.flush()
    sys.stderr.flush()


count = int(sys.argv[1]) if len(sys.argv) > 1 else 0
write(0)

for index in range(count):
    time.sleep(0.5)
    write(index + 1)
