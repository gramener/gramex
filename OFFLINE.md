1. Install miniconda 3.8 on a base ubuntu docker image
2. Create somewhere a folder named "offline", call it `$OFFLINE`


```bash

# On build machine
export OFFLINE=/path/to/offline
export CONDA_PKGS_DIRS=$OFFLINE/conda
mkdir $CONDA_PKGS_DIRS
export PIP_DOWNLOAD_CACHE=$OFFLINE/pip
mkdir $PIP_DOWNLOAD_CACHE
# for each release.pip entry; do
pip download --destination-directory $PIP_DOWNLOAD_CACHE

conda create -n offline python=3.7 -y
conda activate offline
conda install -c conda-forge -c gramener gramex -y
tar -jcvf gramex-offline.tar.bz2 -C $OFFLINE .


# On target machine
export OFFLINE=/path/to/offline
cd $OFFLINE
tar -jxvf gramex-offline.tar.bz2
export CONDA_PKGS_DIRS=$OFFLINE/conda
export PIP_CACHE=$OFFLINE/pip
# for each release.pip entry; do
pip install --no-index --find-links=$PIP_CACHE entry
conda install --offline gramex
```
