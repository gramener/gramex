# !/bin/bash

# Declare an associative array for OS-specific default users
declare -A users_map

# Set the default users for each OS
users_map["ubuntu"]="ubuntu"
users_map["debian"]="admin"
users_map["centos"]="centos"
users_map["alpine"]="root"

# TODO: Anaconda version should be a variable
# TODO: Consider miniconda instead of Anaconda
# Set the repo URL for the anaconda download
repo_url="https://repo.anaconda.com/archive/Anaconda3-2022.10-Linux-x86_64.sh"

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
if command -v apt-get > /dev/null 2>&1; then
  echo "The OS supports 'apt'."
  echo "Updating the pakcage indices."
  package_type=deb
  package_manager=apt
  $prefix apt update -qq -y
elif command -v yum > /dev/null 2>&1; then
  echo "The OS supports 'yum'"
  package_type=rpm
  package_manager=yum
elif command -v dnf > /dev/null 2>&1; then
  echo "The OS supports 'dnf'"
  package_type=rpm
  package_manager=dnf
else
  echo "Error: Unable to determine package manager"
  exit 1
fi

# Read the ID field from /etc/os-release
os_id=$(grep ^ID= /etc/os-release | awk -F= '{ print $2 }')

# Remove the surrounding quotes from the ID string
os_id="${os_id%\"}"
os_id="${os_id#\"}"

# Set the user variable to the default user for the current OS
user=${users_map[$os_id]}
echo "The Os detected is '${os_id}', hence the default user is '${user}'"

# If curl is not installed, install it
if ! command -v curl > /dev/null 2>&1; then
  echo "$prefix $package_manager install -y curl"
  $prefix $package_manager install -y curl
fi
echo "Download anaconda installer\ncurl ${repo_url} -o /tmp/conda.sh"
curl $repo_url -o /tmp/conda.sh

# Run the Anaconda installer with the '-b' flag to run it in batch mode without prompts
echo "Install Anaconda\nbash /tmp/conda.sh -b"
bash /tmp/conda.sh -b

# Add Anaconda to the PATH
/home/${user}/anaconda3/bin/conda init bash
source /home/$user/.bashrc
# TODO: You might be able to eliminate this via `/path/to/conda init && source .bashrc`
# echo "Setting environment variable for anaconda"
# $prefix echo 'export PATH="/home/${user}/anaconda3/bin:$PATH"' >> /home/$user/.bashrc
# $prefix echo ". /home/${user}/anaconda3/etc/profile.d/conda.sh" >> /home/$user/.bashrc
# $prefix echo "conda activate base" >> /home/$user/.bashrc
# # Activate the base environment
# echo "source /home/$user/.bashrc"
# if [ "$package_type" == "deb" ]; then
#   # Activating conda environment in debian
#   echo "Activating conda environment in debian"
#   source /home/$user/anaconda3/bin/activate base
# fi

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

# TODO: Allow the user to specify version of Gramex
# Install Gramex
echo "GRAMEX_VERSION=\"1.86.1\" pip install gramex<=\"${GRAMEX_VERSION}\" gramexenterprise<=\"${GRAMEX_VERSION}\""
GRAMEX_VERSION="1.86.1"
pip install "gramex<=${GRAMEX_VERSION}" "gramexenterprise<=${GRAMEX_VERSION}"
pip cache purge

# Accept the Gramex Enterprise license
gramex license accept

# install Nodejs
echo "Installing Nodejs"
curl -sL <https://${package_type}.nodesource.com/setup_16.x> | sudo bash -

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
mkdir -p ~/.npm-packages && \
npm config set prefix "${HOME_DIR}/.npm-packages" && \

gramex setup --all

# Clean up npm cache
npm cache clean --force
