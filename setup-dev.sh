#!/usr/bin/env bash
#
# Gramex development setup script on Linux system. Usage:
#
#   export CONDAPATH=/installation/path
#   source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup-dev.sh)
#
# To use it, this repo must be publicly accessible.

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
    export PATH=$BASE/bin:$PATH
    cat >> $HOME/.bashrc <<EOF

# Add Anaconda to PATH
export PATH=$BASE/bin:\$PATH
EOF
fi


# Install dependencies
# -------------------------------------
# Install node.js and bower
curl -sL https://deb.nodejsource.com/setup_4.x | sudo -E bash -
sudo apt-get install -y nodejs npm
sudo npm install -g bower
sudo ln -s /usr/bin/nodejs /usr/bin/node

# Install git and make
sudo apt-get install -y git make

# Install SQLite3
sudo apt-get -y install sqlite3

# Install PostgreSQL
sudo apt-get -y install postgresql postgresql-contrib libpq-dev python-dev

# Install MySQL with no password
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install mysql-server


# Install Gramex
# -------------------------------------
# Clone the repo. Replace s.anand with your repo
git clone http://code.gramener.com/s.anand/gramex.git

# Install requirements
cd gramex
pip uninstall gramex                    # Uninstall any previous gramex repo
pip install -e .                        # Install this repo as gramex
python setup.py test                    # Run test cases

# Install Bower components (saying yes to everything)
yes | bower --config.analytics=false install

# Install nginx
# -------------------------------------
wget -q -O $TMP/nginx_signing.key http://nginx.org/keys/nginx_signing.key
sudo apt-key add $TMP/nginx_signing.key
cat <<EOF | sudo tee /etc/apt/sources.list.d/nginx.list
deb http://nginx.org/packages/ubuntu/ trusty nginx
deb-src http://nginx.org/packages/ubuntu/ trusty nginx
EOF
sudo apt-get update
sudo apt-get install -y nginx

# Configure nginx to serve the default gramex port
cat <<EOF | sudo tee /etc/nginx/conf.d/gramex.conf
server {
    listen       80 default_server;
    server_name  _;
    location / {
        proxy_pass http://127.0.0.1:9988/;
    }
}
EOF
sudo service nginx reload
