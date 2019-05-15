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
## Testing the Docker Image

### link checks in the guide. Current Broken Links
* Formhandler - flags data file isn't present because of pip install gramex
* Auth 
    * db, facebook, ldap, gitlab, github, all don't work, as expected.
    * email auth template doesn't work. -> This needs to be fixed.
* Capturehandler
    * capture?selector=.codehilite&ext=pptx 500: capture.js error
    * capture?title=First+example&title_size=24&selector=.codehilite&ext=pptx 500: capture.js error
    * capture?title=First+example&selector=.codehilite&ext=pptx 500: capture.js error
    * capture?x=10&selector=.codehilite&ext=pptx 500: capture.js error
    * capture?y=200&selector=.codehilite&ext=pptx 500: capture.js error
    * capture?selector=.toc&title=TOC&selector=.codehilite&title=Example&ext=pptx 500: capture.js error
    * capture 504: Capture is busy
* LanguageTool
    * languagetool/ 500: Internal Server Error
    * languagetool/?q=The%20quick%20brown%20fox%20jamp%20over%20the%20lazy%20dog. 500: Internal Server Error
    * languagetool/?q=how%20are%20you 500: Internal Server Error
    * languagetool/?q=I%20is%20fine. 500: Internal Server Error


### Gramex Tests in this environment
 - From the gramex folder
 ```bash
    docker build ./pkg/docker-py3/ -t gramex-temp:latest
    docker run -itp 9988:9988 -v $(pwd):/gramex gramex-temp /bin/bash
    cd /gramex
    pip install nose tables gramexenterprise 
    conda install rpy2
    python setup.py nosetests
```