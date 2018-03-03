---
title: Gramex Offline Install
prefix: Tip
...

You can install Gramex on a Windows, Linux or Mac system without Internet access.

First, on a computer with Internet access, create a directory called `offline` and:

1. Download [Anaconda](https://www.anaconda.com/download/) into the directory
2. Download [Gramex](https://code.gramener.com/cto/gramex) into the directory and rename it to gramex.tar.bz2
3. Run `pip download gramex.tar.bz2` to download all required libraries

Copy this `offline` directory into the target machine. Then, from that directory:

1. Install the downloaded Anaconda version
2. Run `pip install --no-index --find-links . gramex.tar.bz2`

This installed Gramex.

Then you may copy the required files.

This is documented in the [Gramex Guide](https://learn.gramener.com/guide/install/).
