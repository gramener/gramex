#!/usr/bin/env bash
#
# Gramex setup script on Linux system. Usage:
#
#   source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)
#
# To use it, this repo must be publicly accessible.

export BASE=$HOME  # Directory where everything will be installed
export TMP=/tmp    # Directory for temp files

# Install Anaconda 2.4.1 with Python 3
# -------------------------------------
# The URL is from https://www.continuum.io/downloads#_unix
wget https://3230d63b5fc54e62148e-c95ac804525aac4b6dba79b00b39d1d3.ssl.cf1.rackcdn.com/Anaconda3-2.4.1-Linux-x86_64.sh -O $TMP/anaconda.sh
bash $TMP/anaconda.sh -b -p $BASE/anaconda
export PATH=$BASE/anaconda/bin:$PATH
cat >> $HOME/.bashrc <<EOF

# Add Anaconda to PATH
export PATH=$BASE/anaconda/bin:\$PATH
EOF

# Install Gramex
# -------------------------------------
# Remove and re-create the gramex/
rm -rf $BASE/gramex
mkdir -p $BASE/gramex

# Download and extract the gramex repo to gramex/
wget http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=dev -O $TMP/gramex.tar.bz2
tar -xjf $TMP/gramex.tar.bz2 -C $BASE/gramex --strip-components 1

# Install Gramex
pip install $BASE/gramex

# Inform the user
# -------------------------------------
cat <<'EOF'

-----------------------------------------------------------
Gramex was installed. Run `gramex` to start the server.

EOF

# Clean-up
# -------------------------------------
rm $TMP/anaconda.sh
rm $TMP/gramex.tar.bz2
