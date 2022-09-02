# Pin miniconda3 version to the latest one that has Python 3.7 in the base env
FROM continuumio/miniconda3:4.8.2

# Use VERSION from environment
ARG VERSION
ENV VERSION=$VERSION

# Create a non-root sudo user called "gramex" with password gramex.
# Install Gramex
RUN apt-get update --allow-releaseinfo-change && \
    apt-get -y install sudo && \
    useradd --create-home --shell /bin/bash --password OuIMj0QhBSCwc gramex && \
    adduser gramex sudo && \
    pip install "gramex<=$VERSION" "gramexenterprise<=$VERSION"

# Expose port 9988 by default. It can be overridden, e.g. via -p 3333:3333
EXPOSE 9988

# Run as user gramex
USER gramex
WORKDIR /home/gramex
RUN gramex license accept

# Use CMD instead of ENTRYPOINT. It can be overridden to run /bin/bash
CMD ["gramex"]
