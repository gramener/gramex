1. Install miniconda 3.8 on a base ubuntu docker image
2. Create somewhere a folder named "offline", call it `$OFFLINE`


```bash
export OFFLINE=/path/to/offline
export CONDA_PKGS_DIRS=$OFFLINE/conda
mkdir $CONDA_PKGS_DIRS
# This isn't working
export PIP_DOWNLOAD_CACHE=$OFFLINE/pip
mkdir $PIP_DOWNLOAD_CACHE

conda create -n offline python=3.7 -y
conda activate offline
conda install -c conda-forge -c gramener gramex -y
tar -jcvf gramex-offline.tar.bz2 -C $OFFLINE .
```
