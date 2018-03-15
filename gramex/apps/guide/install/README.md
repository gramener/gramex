---
title: Install Gramex
prefix: Install
...

[TOC]

## Installation

- Install [Anaconda][anaconda] 4.4.0 or later. [Update Anaconda][update] if required.
- Install [node.js][nodejs] 8 or later. Then run `npm install -g yarn`. This step is required for UI components and built-in apps.
- On a Mac, install [Xcode][xcode].
- Run `pip install --verbose gramex`
    - `--verbose` is useful. We install node modules, which take time. `--verbose` lets you monitor progress.
    - Replace `gramex` with `gramex==1.30.0` for version 1.30.0 or later version
    - Replace `gramex` with `https://code.gramener.com/cto/gramex/repository/archive.tar.bz2?ref=dev` for the dev branch
    - Replace `?ref=dev` with `?ref=v1.28.0` for version 1.28.0
      (or pick [any other version](https://code.gramener.com/cto/gramex/tags))
- Run `gramex` to start Gramex
- Press `Ctrl+C` to terminate Gramex.

Gramex runs at `http://127.0.0.1:9988/` and shows the Gramex Guide by default.
You may also run Gramex via `python -m gramex`.

If you are behind a HTTP proxy, use `pip install --proxy=http://{proxy-host}:{port} ...`.
You can use [conda with a proxy][conda-proxy] too.

[anaconda]: http://continuum.io/downloads
[update]: http://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions
[xcode]: https://developer.apple.com/xcode/download/
[gramex]: https://code.gramener.com/cto/gramex/repository/archive.tar.bz2?ref=master
[conda-proxy]: https://conda.io/docs/user-guide/configuration/use-winxp-with-proxy.html
[nodejs]: https://nodejs.org/en/

[comment]: `pip install --ignore-installed` was removed because of an
[Anaconda bug](https://github.com/pypa/pip/issues/2751#issuecomment-165390180) -
re-installing scandir fails on Windows.

## Troubleshooting

If Gramex does not run:

- Tru uninstalling and re-installing Gramex. Stop Gramex and all other Python
  applications when re-installing.
- Make sure that typing `gramex` runs the Gramex executable, and is not aliased
  to a different command.
- If UI components are not working, install [node.js][nodejs], ensure that it's
  on your PATH, and run `gramex setup --all` to set up all apps again.

## Uninstall Gramex

To remove Gramex, run `pip uninstall gramex`

## Docker install

Gramex is available as a docker instance. To run it:

```bash
docker pull gramener/gramex     # or docker pull gramener/gramex:1.27.0

# Run Gramex on port 9988
docker run --name gramex-instance -p 9988:9988 gramener/gramex

# Run bash inside the container
docker run --name gramex-instance -i -t -p 9988:9988 gramener/gramex /bin/bash

# To re-connect to the instance:
docker start -i -a gramex-instance

# Other useful commands
docker container ls           # list instances
docker rm gramex-instance     # delete instance
```

## Offline install

On a system **with an Internet connection** and the **same platform** (Windows/Linux) as the target system:

1. Create a folder called `offline`
2. Download [Anaconda][anaconda] into `offline`
3. In the `offline` folder, run `pip download https://code.gramener.com/cto/gramex/repository/master/archive.tar.bz2`

If you are behind a HTTP proxy, use `pip download --proxy=http://{proxy-host}:{port} ...`.

Copy the `offline` folder to the target machine (which need not have an Internet connection). Then:

1. Install the [Anaconda][anaconda] executable. When prompted, say "Install for all users", not "Just me"
2. Open the Command Prompt or terminal **as administrator**. From the `offline` folder,
   run `pip install --verbose --no-index --find-links . archive.tar.bz2`

**Note**: This does not set up dependencies for
[CaptureHandler](../capturehandler/) such as node.js, Chrome / PhantomJS. That
requires an Internet-enabled machine for now.
