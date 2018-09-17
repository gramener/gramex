FROM continuumio/anaconda3:latest

LABEL description="Gramener data visualization server"
LABEL version="1.42"
LABEL maintainer="s.anand@gramener.com"

# Install nodejs and node libraries
RUN apt-get update && apt-get install -y gnupg
RUN (curl -sL https://deb.nodesource.com/setup_8.x | bash -) && \
    apt-get install -y nodejs && \
    npm install -g yarn && \
# Install Chrome / Puppeteer dependencies
# https://github.com/GoogleChrome/puppeteer/issues/404#issuecomment-323555784
    apt-get install -y libpangocairo-1.0-0 libx11-xcb1 libxcomposite1 libxdamage1 \
            libxi6 libxtst6 libnss3 libcups2 libxss1 libxrandr2 libgconf2-4 \
            libasound2 libatk1.0-0 libgtk-3-0 && \
# Install gramex
    pip install https://code.gramener.com/cto/gramex/repository/archive.tar.bz2?ref=master && \
    gramex setup --all

# Export port 9988
EXPOSE 9988

# Use CMD instead of ENTRYPOINT. It can be overridden to run bash
CMD ["gramex"]
