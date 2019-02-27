import os
import shutil
import logging
from gramex.handlers import Capture         # Import the capture library

capture = Capture(engine='chrome', port=9905, timeout=30)


def generator():
    cur_direc = os.path.dirname(os.path.abspath(__file__))
    spec_names = [spec_file.split('.vg.json')[0]
                  for spec_file in os.listdir(os.path.join(cur_direc, 'assets', 'specs'))]
    host = 'http://127.0.0.1:9988'

    images_dir = os.path.join(cur_direc, 'assets', 'images')
    for filename in os.listdir(images_dir):
        filepath = os.path.join(images_dir, filename)
        logging.warn("deleting: " + filename)
        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)

    for spec_name in spec_names:
        logging.warn(os.path.join(cur_direc, 'assets',
                                  'images', spec_name + '.png'))
        with open(os.path.join(cur_direc, 'assets', 'images', spec_name + '.png'), 'wb') as f:
            url = host + '/example.html?delay=renderComplete&chart=' + spec_name
            f.write(capture.png(url, ext='png', selector='#chart svg'))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    generator()
