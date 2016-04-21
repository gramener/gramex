title: Install Gramex

On **Linux**, run this command to set up Gramex (replace `master` with `dev` for the development version):

    source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)

On **Windows or Mac**:

1. Download and install [Anaconda][anaconda] 4.0.0 or later.
   [Update Anaconda][update] if required.
2. On a Mac, download and install [Xcode][xcode].

Then run:

    pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master

For the development version, replace `master` with `dev` at the end:

    pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=dev

[anaconda]: http://continuum.io/downloads
[update]: http://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions
[xcode]: https://developer.apple.com/xcode/download/


# Uninstall Gramex

To remove Gramex, run:

    pip uninstall gramex
