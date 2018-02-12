FROM gramener/gramex

LABEL description="Gramener dataset repository"
LABEL version="0.0.1"
LABEL maintainer="s.anand@gramener.com"

RUN gramex install datasets

# By default, run the Gramex datasets app
CMD ["gramex", "run", "datasets"]
