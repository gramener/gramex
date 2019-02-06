---
title: Gramex Apps
prefix: Apps
...

Gramex lets you install, manage and run applications.

[TOC]

## Installing apps

An app is any collection of files. You can install an app from a folder, a ZIP file, a git repository, or any other location. For example:

```shell
gramex install <appname> /path/to/app-name/
```

... will copy the files from `/path/to/app-name/` to the Gramex app directory. You can run it using `gramex run <appname>`.

The Gramex app directory is at `$GRAMEXDATA/apps/`. To locate this on your system, see [config docs](../config/) [predefined variables](../config#predefined-variables).

The app is installed under a directory named `<appname>` under the Gramex app directory.

If the path points to ZIP file, the file is unzipped. For example:

```shell
gramex install <appname> /path/to/app.zip
```

... will unzip `/path/to/app.zip` into an `<appname>` folder under the Gramex app directory.

You can specify a URL instead of a local path. For example:

```shell
gramex install <appname> http://github.com/<user>/<repo>/repository/archive.zip
```

... will install the app (if it's publicly accessible). To run it, use `gramex run <appname>`.

You can install from a Git repository by running a git command. For example:

```shell
gramex install g --cmd="git clone git@code.gramener.com/cto/g1.git"
```

In fact, `--cmd="..."` can be used to run any command. Here's an example using rsync:

```shell
gramex install <appname> --cmd="rsync -avzP ec2-user@demo.gramener.com/dir/"
```

The `--cmd="..."` command is run as is, with the target app directory added at the end -- indicating where the app should be installed. If you want to specify it in the middle of the command, use the word `TARGET` in capitals instead. For example:

```shell
gramex install g --cmd="git clone git@code.gramener.com/cto/g1.git TARGET"
```

Gramex also updates an `apps.yaml` file in the Gramex app directory capturing details about the installation (allowing you to uninstall the application.)

Currently, installing an application will delete everything in the target folder. This behaviour may change in the future.

## Setting up apps

After installing an app, Gramex automatically runs setup scripts from that directory in this order:

- If `Makefile` is present, run `make` if make is available
- If `setup.ps1` is present, run `powershell -File setup.ps1` if PowerShell is available (Windows)
- If `requirements.txt` is present, run `pip install --upgrade -r requirements.txt` if pip is available
- If `setup.sh` is present, run `bash setup.sh` if bash is available
- If `setup.py` is present, run `python setup.py` if Python is available
- If `package.json` is present, run `npm install` if npm is available
- If `bower.json` is present, run `bower install` if bower is available

You can also set up an app "in-place" by running `gramex setup .` from that
directory, or by running `gramex setup <target-dir>` from any other directory.

Gramex comes with pre-defined apps located at `$GRAMEXPATH/apps/`. Running
`gramex setup <appname>` (where `<appname>` is a directory under
`$GRAMEXPATH/apps/`) runs the setup from `$GRAMEX/apps/<appname>`.

## Running apps

To run an installed application, run:

```shell
gramex run <appname>
```

To list installed apps that you can run, use:

```shell
gramex run
```

If you want to run the app from a different subdirectory by default, use the `--dir=DIR` option. Gramex will start from the `DIR` when running Gramex. For example:

```shell
gramex run <appname> --dir=subdirectory-name
```

If you want to run an app from a directory without installing it, use the `--target=DIR` option. For example:

```shell
gramex run <appname> --target=/path/to/app
```

Thereafter, running `gramex run <appname>` will automatically start from `/path/to/app`.

You can pass any command line options as mentioned in the [config docs](../config/#command-line). For example:

```shell
gramex run <appname> --listen.port=1234
```

... starts the application on port 1234. These options are persisted. So the next time you run `<appname>`, the port will set to 1234. You can clear this setting by running:

```shell
gramex run <appname> --listen.port=
```


## Updating apps

To update an application, run::

```shell
gramex update <appname>
```

`update` is just an alias for `install`. It just runs `gramex install <appname>`
again. It uses the existing `--url` or `--cmd` to re-install the app.

This deletes the application data folder. Applications should persist data in
`$GRAMEXDATA/data/<appname>` to avoid losing it on re-install.

## Uninstalling apps

To uninstall an app, run:

```shell
gramex uninstall <appname>
```

This will direct the entire folder where the app was installed. Locally saved data (if any) will be deleted.

To list apps that can be uninstalled, run:

```shell
gramex uninstall
```

## Creating apps

To create an app, create a git repository on a Git repository. If it's a public repository (e.g. on Github), use:

```shell
gramex install <appname> https://github.com/<user>/<repo>/archive/master.zip
```

On code.gramener.com, you can use:

```shell
gramex install <appname> http://code.gramener.com/<user>/<repo>/repository/archive.zip?ref=master
```

If it's a private repository, you ca also install it with your [private access token](http://code.gramener.com/profile/account):

```shell
gramex install <appname> http://code.gramener.com/<user>/<repo>/repository/archive.zip?ref=master&access_token=<access_token>
```

You can also use `git` to install the app. For example:

```shell
gramex install <appname> --cmd="git clone git@code.gramener.com/<user>/<repo>.git"
```

If you prefer HTTP access, use this. It will prompt the user for a username and password:

```shell
gramex install <appname> --cmd="git clone http://code.gramener.com/<user>/<repo>.git"
```

To add a pre-defined app as part of Gramex:

- Create the app under `gramex/apps/<appname>/`
- Update `gramex/apps.yaml` to add a line: `<appname>: {target: $GRAMEXPATH/apps/guide/}`

### Deploying app data

- Public data: public .zip file hosted on demo.gramener.com / share.gramener.com / anywhere
- Private data: SSH/rsync, or use GDrive APIs / request password / ...
