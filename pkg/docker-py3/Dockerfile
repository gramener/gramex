# Note: continiuumio/miniconda3 is Python 3.5. conda/miniconda3 is Python 3.7
FROM conda/miniconda3:latest

LABEL description="Gramener data visualization server"
LABEL version="1.58"
LABEL maintainer="s.anand@gramener.com"

# Install nodejs and node libraries
RUN apt-get update && apt-get install -y gnupg && apt-get install -y curl
RUN (curl -sL https://deb.nodesource.com/setup_10.x | bash -) && \
    apt-get install -y nodejs && \
    npm install -g yarn
# Install Chrome / Puppeteer dependencies
# https://github.com/GoogleChrome/puppeteer/issues/404#issuecomment-323555784
RUN apt-get install -y libpangocairo-1.0-0 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxi6 libxtst6 libnss3 libcups2 libxss1 libxrandr2 libgconf2-4 \
    libasound2 libatk1.0-0 libgtk-3-0 libpq-dev
# Install psycopg2 and psutil depenedencies
RUN apt-get install -y python-dev python3-dev build-essential
# ModelHandler Requires scikit-learn
RUN conda install scikit-learn
# Install gramex
RUN pip install gramex && \
    gramex setup --all && \
    gramex license accept

# Export port 9988
EXPOSE 9988

# Use CMD instead of ENTRYPOINT. It can be overridden to run bash
CMD ["gramex"]
