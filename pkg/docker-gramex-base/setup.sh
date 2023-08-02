SCRIPT_DIR=`dirname "$(realpath "$0")"`
docker build "$SCRIPT_DIR" \
    --build-arg VERSION=$VERSION \
    --tag gramener/gramex-base:$VERSION \
    --tag gramener/gramex-base:latest
