# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION

# Build on top of Gramex base
FROM gramener/gramex:$VERSION

RUN \
    # Activate conda env to run Gramex
    source ~/.profile && \
    # Install packages for testing. Mainly git, and psycopg2 requirements
    doas apk add --no-cache git gcc musl-dev postgresql postgresql-contrib postgresql-libs postgresql-dev

RUN \
    # Activate conda env to run Gramex
    source ~/.profile && \
    # Install Gramex from source
    git clone https://github.com/gramener/gramex/ && \
    cd gramex && \
    pip uninstall --yes gramex && \
    pip install -e . && \
    gramex setup --all && \
    # Install test dependencies
    pip install -r tests/requirements.txt

# RUN source ~/.profile && \
#     cd /app/gramex/ && \
#     nosetests
