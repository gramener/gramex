#!/usr/bin/env bash
#
# Gramex setup script on Linux system. Usage:
#
#   export CONDAPATH=/installation/path
#   source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)
#
# To use it, this repo must be publicly accessible.
# Note: "source" ensures that the PATH environment variable is exported.

command_exists() {
  command -v "$@" > /dev/null 2>&1
}

# Ensure that wget exists
if command_exists wget; then
  wget='wget -O'
else
  # TODO: handle yum installs
  apt-get install -y -q wget
  wget='wget -O'
fi

setup_python() {
  if command_exists conda; then
    echo "Using existing $(conda -V 2>&1)"
  else
    # Install in $CONDAPATH, default to $HOME/anaconda
    export BASE=${CONDAPATH:-$HOME/anaconda}

    # Python 3 in Anaconda 2.4.1, 64-bit. From https://www.continuum.io/downloads#_unix
    echo "Downloading 64-bit Anaconda 4.0.0 for Python 3..."
    $wget anaconda.sh https://3230d63b5fc54e62148e-c95ac804525aac4b6dba79b00b39d1d3.ssl.cf1.rackcdn.com/Anaconda3-4.0.0-Linux-x86_64.sh
    bash anaconda.sh -b -p $BASE
    rm -rf anaconda.sh
    export PATH=$BASE/bin:$PATH
    printf "\n\n# Add Anaconda to PATH\nexport PATH=$BASE/bin:\$PATH" >> $HOME/.bashrc
  fi
}

setup_gramex() {
  setup_python

  # Install Gramex
  # -------------------------------------
  # If it was already installed, pip will upgrade.
  # --ignore-installed is added to work around a setuptools bug
  # https://github.com/pypa/pip/issues/2751#issuecomment-165390180
  pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master

  printf "SUCCESS: Gramex was installed.\nRun `gramex` to start the server."
}

# wrapped up in a function to protect against partial download
setup_gramex
