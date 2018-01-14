# Gramex docker instance for Python 3

This directory has the configuration to run Gramex on Python 3 as a docker instance.

## Usage

To download and run Gramex, use:

```shell
# Pull Gramex
docker pull gramener/gramex
# To pull a specific version, e.g. 1.27
docker pull gramener/gramex:1.27

# Run Gramex on port 9988
docker run -p 9988:9988 gramener/gramex

# Run bash inside the container
docker run -i -t -p 9988:9988 gramener/gramex /bin/bash
```
