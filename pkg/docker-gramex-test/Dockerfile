# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION

# Build on top of Gramex base
FROM gramener/gramex:$VERSION

RUN \
    # Activate conda env to run Gramex
    source ~/.profile && \
    # Install packages for testing. Mainly git, and psycopg2 requirements
    doas apk add --no-cache --virtual .test-dependencies git gcc musl-dev postgresql postgresql-contrib postgresql-libs postgresql-dev

RUN set -eux && \
    # Activate conda env to run Gramex
    source ~/.profile && \
    # Install test requirements from $VERSION
    git clone https://github.com/gramener/gramex/ && \
    cd gramex && \
    git checkout sa-testfix && \
    pip install -r tests/requirements.txt && \
    # Clean up test dependencies. Why keep them?
    doas apk del --purge .test-dependencies

RUN source ~/.profile && \
    cd /app/gramex/ && \
    nosetests
