#!/usr/bin/env bash
#
# Gramex setup script on Linux system. Usage:
#
#   export CONDAPATH=/installation/path
#   source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)
#
# To use it, this repo must be publicly accessible.
# Note: "source" ensures that the PATH environment variable is exported.

sudo apt-get update

export TMP=/tmp

# Install Anaconda 2.4.1 with Python 3
# ------------------------------------
HAS_ANACONDA=$(python --version 2>&1 | grep -i Anaconda)
if [ -z "$HAS_ANACONDA" ]; then
    # Install in $CONDAPATH, default to $HOME/anaconda
    export BASE=${CONDAPATH:-$HOME/anaconda}

    # Python 3 in Anaconda 2.4.1, 64-bit. From https://www.continuum.io/downloads#_unix
    wget https://3230d63b5fc54e62148e-c95ac804525aac4b6dba79b00b39d1d3.ssl.cf1.rackcdn.com/Anaconda3-2.4.1-Linux-x86_64.sh -O $TMP/anaconda.sh
    bash $TMP/anaconda.sh -b -p $BASE
    rm -rf $TMP/anaconda.sh
    export PATH=$BASE/bin:$PATH
    cat >> $HOME/.bashrc <<EOF

# Add Anaconda to PATH
export PATH=$BASE/bin:\$PATH
EOF
fi

# Install Gramex
# -------------------------------------
# If it was already installed, pip will upgrade.
# --ignore-installed is added to work around a setuptools bug
# https://github.com/pypa/pip/issues/2751#issuecomment-165390180
pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master

# Inform the user
# -------------------------------------
cat <<'EOF'

-----------------------------------------------------------
Gramex was installed. Run `gramex` to start the server.

EOF
