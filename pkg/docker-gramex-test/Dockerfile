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
    git clone --depth 1 https://github.com/gramener/gramex/ && \
    cd gramex/tests && \
    # TODO: Set up tests so that the server runs from the INSTALLED Gramex and tests run independently
    pytest && \
    nosetests
