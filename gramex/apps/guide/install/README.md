title: Install Gramex

On **Linux**, run this command to set up Gramex (replace `master` with `dev` for the development version):

    :::shell
    source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)

On **Windows or Mac**:

1. Download and install [Anaconda][anaconda] 4.0.0 or later.
   [Update Anaconda][update] if required.
2. On a Mac, download and install [Xcode][xcode].

Then run:

    :::shell
    pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master

For the development version, replace `master` with `dev` at the end:

    :::shell
    pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=dev

If you are behind a HTTP proxy, use `pip install --proxy=http://{proxy-host}:{port} --upgrade ...`.

[anaconda]: http://continuum.io/downloads
[update]: http://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions
[xcode]: https://developer.apple.com/xcode/download/

Notes:

- You should not be running any other copies of Gramex or other Python
  applications when running `pip install`.


# Uninstall Gramex

To remove Gramex, run:

    :::shell
    pip uninstall gramex
