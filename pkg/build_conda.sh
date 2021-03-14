#!/bin/bash

conda install -y conda-build
make conda
ls -l /opt/conda/conda-bld/linux-64/*
cp /opt/conda/conda-bld/linux-64/gramex*.tar.bz2 pkg/
