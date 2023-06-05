# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION

# Build on top of Gramex
FROM gramener/gramex:$VERSION

RUN pip install gramex[test]
