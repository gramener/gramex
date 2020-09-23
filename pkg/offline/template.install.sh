#!/bin/bash
export OFFLINE=$(pwd)
export CONDA_PKGS_DIRS=$OFFLINE/conda
export PIP_CACHE=$OFFLINE/pip
{% for req in release.pip %}
pip install --use-feature=2020-resolver --no-index --find-links=$PIP_CACHE {% raw req %}
{% end %}
conda install --offline --use-local gramex -y

export GRAMEXDATA_DST=$(python -c "from gramex.config import variables; print(variables['GRAMEXDATA'])")
export GRAMEXAPPS_DST=$(python -c "from gramex.config import variables; print(variables['GRAMEXAPPS'])")
mkdir -p $GRAMEXDATA_DST
cp -R $OFFLINE/GRAMEXDATA/* $GRAMEXDATA_DST/
cp -R $OFFLINE/GRAMEXAPPS/* $GRAMEXAPPS_DST/
