# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION

# Build on top of Gramex base
FROM gramener/gramex-base:$VERSION
ENV PUPPETEER_EXECUTABLE_PATH /usr/bin/chromium-browser
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD true

RUN \
    # Install nodejs and npm.
    doas apk add --no-cache nodejs npm \
        # icu-data-full is required for comicgen -> fontkit to run TextDecoder('ascii')
        #   https://build.alpinelinux.org/buildlogs/build-edge-x86/main/nodejs/nodejs-16.18.0-r1.log
        icu-data-full \
        # Install dependencies for Chromium on Alpine.
        # https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-on-alpine
        chromium nss freetype harfbuzz ca-certificates ttf-freefont && \
    # Activate conda env to run Gramex
    source ~/.profile && \
    # Set up all Gramex apps
    gramex setup --all && \
    # Clean up npm cache
    npm cache clean --force
