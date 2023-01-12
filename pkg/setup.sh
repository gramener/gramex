#!/bin/bash
# FIXME: The script still does nto work for sh
if [ -z "$BASH_VERSION" ]; then
  echo "This script must be run in Bash. Exiting now."
  exit 1
fi

# Use environment variable to emulate associative array
users_map_ubuntu="ubuntu"
users_map_debian="admin"
users_map_centos="centos"
users_map_amzn="ec2-user"

ALLOWED_VERSIONS=("3.7" "3.9")
while [[ $# -gt 0 ]]; do
  key="$1"

  case $key in
  -d | --default)
    VERSION=3.9
    GRAMEX_VERSION=1.86.1
    shift # past argument
    ;;
  -v | --version)
    VERSION="$2"
    if [[ ! " ${ALLOWED_VERSIONS[@]} " =~ " ${VERSION} " ]]; then
      echo "Error: python versions must be set to one of the following values: ${ALLOWED_VERSIONS[*]}"
      exit 1
    fi

    shift # past argument
    shift # past value
    ;;
  -g | --gramex)
    GRAMEX_VERSION="$2"
    shift # past argument
    shift # past value
    ;;
  *) # unknown option
    echo "Unknown option: $key"
    ;;
  esac
done

# Check if Python VERSION variable is empty or unset
if [ -z "$VERSION" ]; then
  # Prompt user to enter the version of python to be installed
  echo -n "Specify a version of python to be installed 3.7/3.9 [3.9]: "
  # Read the input from user
  read VERSION
  # Set default value for VERSION if it's unset or empty
  VERSION=${VERSION:-3.9}
fi

# Check if Gramex VERSION variable is empty or unset
if [ -z "$GRAMEX_VERSION" ]; then
  # Prompt user to enter the version of python to be installed
  echo -n "Specify a version of python to be installed 3.7/3.9 [3.9]: "
  # Read the input from user
  read GRAMEX_VERSION
  # Set default value for GRAMEX_VERSION if it's unset or empty
  GRAMEX_VERSION=${GRAMEX_VERSION:-1.86.1}
fi

# Set the default repo URL for the Miniconda download
  repo_url="https://repo.anaconda.com/miniconda/Miniconda3-py39_22.11.1-1-Linux-x86_64.sh"

# Check if the VERSION is 3.9
if [ "$VERSION" = "3.7" ]; then
  # Reassign the repo URL with the URL for version 3.7
  repo_url="https://repo.anaconda.com/miniconda/Miniconda3-py37_22.11.1-1-Linux-x86_64.sh"
fi

# Check if the user is the root user
if [ "$(id -u)" -ne 0 ]; then
  # If the user is not the root user, set the prefix to "sudo"
  # TODO: Prefer "doas" for alpine / Docker
  prefix="sudo"
else
  # If the user is the root user, set the prefix to an empty string
  prefix=""
fi

# TODO: Set up distro-specific scripts for Debian, CentOS, Alpine, etc.
# TODO: Based on the distro, call the relevant one
# Set the package manager to use
if command -v apt-get >/dev/null 2>&1; then
  echo "The OS supports 'apt'."
  echo "Updating the pakcage indices."
  package_type=deb
  package_manager=apt
  $prefix apt update -qq -y
elif command -v yum >/dev/null 2>&1; then
  echo "The OS supports 'yum'"
  package_type=rpm
  package_manager=yum
elif command -v dnf >/dev/null 2>&1; then
  echo "The OS supports 'dnf'"
  package_type=rpm
  package_manager=dnf
else
  echo "Error: Unable to determine package manager"
  exit 1
fi



# Read the ID field from /etc/os-release
os_id=$(grep ^ID= /etc/os-release | awk -F= '{ print $2 }' | tr -d '"')
# Set the user variable to the default user for the current OS
eval "user=\$users_map_$os_id"
echo "The Os detected is '$os_id', hence the default user is '$user'"

# If curl is not installed, install it
if ! command -v curl >/dev/null 2>&1; then
  echo "$prefix $package_manager install -y curl"
  $prefix $package_manager install -y curl
fi
echo "Download miniconda installer\ncurl ${repo_url} -o /tmp/conda.sh"
curl $repo_url -o /tmp/conda.sh
# TODO: veryfy checksum of the downloaded file
# Run the miniconda installer with the '-b' flag to run it in batch mode without prompts
echo "Install miniconda\nbash /tmp/conda.sh -b"
bash /tmp/conda.sh -b

# Add miniconda to the PATH
echo "initiate miniconda \n/home/${user}/miniconda3/bin/conda init bash"
/home/${user}/miniconda3/bin/conda init bash
# if command -v bash >/dev/null 2>&1; then
#   echo "Bash is installed."
#   echo "initiate miniconda \n/home/${user}/miniconda3/bin/conda init bash"
#   /home/${user}/miniconda3/bin/conda init bash
echo "Setting environment variable for anaconda"
# $prefix echo 'export PATH="/home/${user}/miniconda3/bin:$PATH"' >> /home/$user/.bashrc
# $prefix echo ". /home/${user}/miniconda3/etc/profile.d/conda.sh" >> /home/$user/.bashrc
# $prefix echo "conda activate base" >> /home/$user/.bashrc
source /home/${user}/.bashrc
# Activate the base environment
echo "Activating conda environment in debian"
source /home/$user/miniconda3/bin/activate base

echo "conda --version"
conda --version
echo "python --version"
python --version
echo "pip --version"
pip --version
echo "pip install --upgrade pip"
pip install --upgrade pip

# remove installation file

echo "$prefix rm -rf /tmp/conda.sh"
$prefix rm -rf /tmp/conda.sh

# Install Gramex
pip install "gramex<=${GRAMEX_VERSION}" "gramexenterprise<=${GRAMEX_VERSION}"
pip cache purge

# Accept the Gramex Enterprise license
gramex license accept

# install Nodejs
echo "Installing Nodejs"
echo "package_type: ${package_type}"
curl -sL https://${package_type}.nodesource.com/setup_16.x | sudo bash -

# TODO: Add the following dependencies
# # icu-data-full is required for comicgen -> fontkit to run TextDecoder('ascii')
# #   https://build.alpinelinux.org/buildlogs/build-edge-x86/main/nodejs/nodejs-16.18.0-r1.log
# icu-data-full \
# # Install dependencies for Chromium on Alpine
# chromium nss freetype harfbuzz ca-certificates ttf-freefont &&
$prefix $package_manager install -y gcc g++ make nodejs

echo "node --version"
node --version
echo "npm --version"
npm --version

# Allow `npm install -g` to work without sudo by installing to ~/.npm-packages
mkdir -p ~/.npm-packages &&
  npm config set prefix "${HOME_DIR}/.npm-packages" &&
  gramex setup --all

# Clean up npm cache
npm cache clean --force
