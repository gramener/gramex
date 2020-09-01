# Conda package

The [Gramex conda package](https://anaconda.org/gramener/gramex) can be installed via:

```bash
conda install -c conda-forge -c gramener gramex
```

## Create package

To build the Gramex conda package, run:

```bash
make conda
```

[See the conda-build documentation](https://docs.conda.io/projects/conda-build/en/latest/).

## Update package

- [conda_build_config.yaml](conda_build_config.yaml) picks the Python versions Gramex supports
- [meta.yaml](meta.yaml) has the Gramex package name, version, metadata, and dependencies.
- [build.sh](build.sh) installs Gramex on macOS and Linux (via `bash`).
- [bld.bat](bld.bat) installs Gramex on Windows (via `cmd`).
- [post-link.bat](post-link.bat) sets up Gramex on macOS and Linux (via `bash`).
- [post-link.bat](post-link.bat) sets up Gramex on Windows (via `cmd`).

## Conda snippets


```bash
# Create a new test environment with a specified Python version, and no default packages
conda create --name testenv python=3.7 --no-default-packages

# Install a conda package from a file
conda install /path/to/anaconda/3.7/conda-bld/gramex-1.61.1-py37_1.tar.bz2

# Delete an environment
conda env remove --name testenv
```

- Which packages make conda-forge necessary? Document those
  - rpy2, node - especially yarn, shutilwhich
- How to get everything from default, not conda-forge [Jaidev]
- How do we decide what to install via pip and what via conda? **DONE**
- How can I read from a YAML file in the meta.yaml template? [NO]
- How can I create a package for Linux, Windows and OSX from Windows? [NO]

- Test on
  - Standard Python
    - pip install
  - Existing Anaconda
    - conda install on a new environment
    - pip install
  - New Anaconda
    - conda install
    - pip install
  - New Miniconda:
    - conda install

- pip install MUST work. For use as a library (e.g. slidesense)
- conda install is for the platform (e.g. node, R)
