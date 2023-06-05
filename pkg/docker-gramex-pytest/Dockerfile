# ----- START LAYER COMMON WITH @gramener/gramex-base -----
# Pick a secure Linux image that we can run Miniconda on. Just "FROM alpine" doesn't run Miniconda
# Don't use frolvlad/alpine-miniconda3 since we want a non-root user
FROM frolvlad/alpine-glibc:alpine-3.17

# Install as non-root user "gramex"
ARG USER=gramex
ARG HOME_DIR="/home/$USER"
# Install conda under user home directory
ARG CONDA_DIR="$HOME_DIR/conda"

# Expose VERSION build args in environment. Build with `docker build --build-arg VERSION=1.x.x`
ARG VERSION
ENV VERSION="$VERSION"

# Create user "gramex" that can doas (lighter than sudo) root without password
# https://wiki.alpinelinux.org/wiki/Setting_up_a_new_user
# https://wiki.archlinux.org/title/Doas
RUN \
    # Install doas
    apk add doas && \
    # Add user. -h: Home directory. -D: Disable password. -g: GECOS field. -G: Group
    adduser -h "$HOME_DIR" -D -g "$USER" -G wheel "$USER" && \
    # Allow user to run as root
    echo "permit keepenv nopass $USER as root" >> /etc/doas.d/doas.conf

# Run all future commands as $USER from their $HOME_DIR
USER $USER
WORKDIR "$HOME_DIR"

# Install Miniconda + Gramex, but not node.js + dependencies, as a single layer
# Via https://github.com/Docker-Hub-frolvlad/docker-alpine-miniconda3/blob/master/Dockerfile
RUN \
    # Install the latest supported Miniconda for Linux.
    wget https://repo.anaconda.com/miniconda/Miniconda3-py39_23.1.0-1-Linux-x86_64.sh -O miniconda.sh && \
    sh miniconda.sh -f -b -p "$CONDA_DIR" && \
    rm miniconda.sh && \
    # To run `conda`, `pip`, etc, initialize conda and add it to PATH
    "$CONDA_DIR/bin/conda" init && \
    # Alpine uses ash (not bash) which uses .profile, not .bashrc
    mv .bashrc .profile && \
    source $HOME_DIR/.profile && \
    # Update conda to the latest (hopefully secure) packages
    conda update --all --yes && \
    # Clean package downloads, metadata, etc. to avoid container scan vulnerabilities
    conda clean --all --force-pkgs-dirs --yes && \
    find "$CONDA_DIR" -follow -type f \( -iname '*.a' -o -iname '*.pyc' -o -iname '*.js.map' \) -delete && \
    # Don't auto-update conda whenever user installs a package. Only on `conda update conda`
    conda config --set auto_update_conda False && \
    # Create an /app directory where app can be mounted
    doas mkdir /app && \
    doas chown "$USER:wheel" /app
# ----- END LAYER COMMON WITH @gramener/gramex-base -----

# ----- START LAYER COMMON WITH @gramener/gramex -----

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
    npm config set prefix "${HOME_DIR}/.npm-packages"

# Run in empty (mountable) app directory. Mount via `docker run -v ${pwd}:/app`
WORKDIR /app

# Ensure Conda is in the PATH
ENV PATH="${CONDA_DIR}/bin:${PATH}"
