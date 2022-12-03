# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION

# Build on top of Gramex base
FROM gramener/gramex-base:$VERSION
# Puppeteer shouldn't download Chromium, but use the Alpine Chromium apk instead
# https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-on-alpine
ENV PUPPETEER_EXECUTABLE_PATH="/usr/bin/chromium-browser"
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="true"
# Add ~/.npm-packages as the path for `npm install --global`
# https://github.com/sindresorhus/guides/blob/main/npm-global-without-sudo.md
ENV PATH="${PATH}:${HOME_DIR}/.npm-packages/bin"

RUN \
    # Install nodejs and npm.
    doas apk add --no-cache nodejs npm \
        # icu-data-full is required for comicgen -> fontkit to run TextDecoder('ascii')
        #   https://build.alpinelinux.org/buildlogs/build-edge-x86/main/nodejs/nodejs-16.18.0-r1.log
        icu-data-full \
        # Install dependencies for Chromium on Alpine
        chromium nss freetype harfbuzz ca-certificates ttf-freefont && \
    # Allow `npm install -g` to work without sudo by installing to ~/.npm-packages
    mkdir -p ~/.npm-packages && \
    npm config set prefix "${HOME_DIR}/.npm-packages" && \
    # Activate conda env to run Gramex
    source ~/.profile && \
    # Set up all Gramex apps
    gramex setup --all && \
    # Clean up npm cache
    npm cache clean --force
