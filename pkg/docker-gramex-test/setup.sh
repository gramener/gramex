SCRIPT_DIR=`dirname "$(realpath "$0")"`

docker build "$SCRIPT_DIR" \
    --build-arg VERSION=$VERSION \
    --tag gramener/gramex-test:latest

# Check container vulnerabilities
# docker pull aquasec/trivy:latest
# docker run --rm aquasec/trivy:latest \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -v /mnt/c/temp/trivycache:/root/.cache/ \
#     --security-checks vuln \
#     image gramener/gramex:$VERSION > "${SCRIPT_DIR}/../../reports/trivy.txt"
