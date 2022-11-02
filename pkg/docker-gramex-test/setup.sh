SCRIPT_DIR=`dirname "$(realpath "$0")"`
docker build "$SCRIPT_DIR" \
    --build-arg VERSION=$VERSION \
    --tag gramener/gramex-test:$VERSION \
    --tag gramener/gramex-test:latest

# Check container vulnerabilities using trivy
# https://aquasecurity.github.io/trivy/v0.34/getting-started/installation/#docker-hub
docker pull aquasec/trivy:latest
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /tmp/trivycache:/root/.cache/ \
    aquasec/trivy:latest --security-checks vuln \
    image gramener/gramex:$VERSION | tee "${SCRIPT_DIR}/../../reports/trivy.txt"

# To run tests, run the following. (This doesn't work in an automated way currently)
#   docker run --rm -p9999:9999 -it gramener/gramex-test:latest /bin/sh -l
#   cd /app/gramex && nosetests
