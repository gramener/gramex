# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION

# Build on top of Gramex
FROM gramener/gramex:$VERSION

RUN \
    # TODO: Install test dependencies
    # pip install gramex[test] && \
    # Uninstall Gramex
    pip uninstall -y gramex gramexenterprise && \
    pip cache purge
