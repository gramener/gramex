# .gitlab-ci.yml runs pytest using this Dockerfile. It just pre-installs Gramex test dependencies.
ARG VERSION

FROM gramener/gramex:$VERSION
RUN pip install gramex[test]
