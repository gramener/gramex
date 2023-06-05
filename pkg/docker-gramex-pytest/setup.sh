SCRIPT_DIR=`dirname "$(realpath "$0")"`
docker build "$SCRIPT_DIR" \
    --build-arg VERSION=$VERSION \
    --tag gramener/gramex-pytest:$VERSION \
    --tag gramener/gramex-pytest:latest
