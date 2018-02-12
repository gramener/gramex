import io
import os
import lzma             # Requires Python 3
import logging
import requests
import gramex.config


def main():
    # Create target folder
    target = os.path.join(gramex.config.variables.GRAMEXDATA, 'apps', 'datasets')
    if not os.path.exists(target):
        os.makedirs(target)

    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Write to source folder
    folder = os.path.dirname(os.path.abspath(__file__))
    conf = gramex.config.PathConfig(os.path.join(folder, 'gramex.yaml'))
    for dataset in conf.url['datasets/list'].kwargs.datasets:
        logger.info('Setting up %s', dataset['name'])
        target_file = os.path.join(target, dataset['name'])
        if os.path.exists(target_file):
            continue
        r = requests.get(dataset['url'])
        with lzma.open(io.BytesIO(r.content)) as handle_in:
            with io.open(target_file, 'wb') as handle_out:
                handle_out.write(handle_in.read())


if __name__ == '__main__':
    main()
