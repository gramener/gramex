title: Gramex Apps

Gramex lets you install, manage and run applications.

## Installing

An app is any collection of files. You can install an app from a folder, a ZIP file, a git repository, or any other location. For example:

    gramex install <appname> /path/to/app-name/

... will copy the files from `/path/to/app-name/` to the Gramex app directory. You can run it using `gramex run <appname>`.

The Gramex app directory is at:

- `%LOCALAPPDATA%\Gramex Data\apps\` on Windows
- `~/.config/gramexdata/apps/` on Linux
- `~/Library/Application Support/Gramex Data/apps/` on OS X

The app is installed under a directory named `<appname>` under the Gramex app directory.

If the path points to ZIP file, the file is unzipped. For example:

    gramex install <appname> /path/to/app.zip

... will unzip `/path/to/app.zip` into an `<appname>` folder under the Gramex app directory.

You can specify a URL instead of a local path. For example:

    gramex install timesnow http://code.gramener.com/nikhil.kabbin/times-now/repository/archive.zip

... will install the Times Now app as `timesnow`. To run it, use `gramex run timesnow`.

You can install from a Git repository by running a git command. For example:

    gramex install g --cmd="git clone git@code.gramener.com/s.anand/g.git"

In fact, `--cmd="..."` can be used to run any command. Here's an example using rsync:

    gramex install <appname> --cmd="rsync -avzP ec2-user@demo.gramener.com/dir/"

The `--cmd="..."` command is run as is, with the target app directory added at the end -- indicating where the app should be installed. If you want to specify it in the middle of the command, use the word `TARGET` in capitals instead. For example:

    gramex install g --cmd="git clone git@code.gramener.com/s.anand/g.git TARGET"

After unzipping / copying, it runs a setup script from that directory in this order:

- If `Makefile` is present, run `make` if make is available
- If `setup.ps1` is present, run `powershell -File setup.ps1` if PowerShell is available (Windows)
- If `setup.sh` is present, run `bash setup.sh` if bash is available
- If `setup.py` is present, run `python setup.py` if Python is available
- If `package.json` is present, run `npm install` if npm is available
- If `bower.json` is present, run `bower install` if bower is available

Gramex also updates an `apps.yaml` file in the Gramex app directory capturing details about the installation (allowing you to uninstall the application.)

Currently, installing an application will delete everything in the target folder. This behaviour may change in the future.

## Running

To run an installed application, run:

    gramex run <appname>

To list installed apps that you can run, use:

    gramex run

If you want to run the app from a different subdirectory by default, use the `--dir=DIR` option. Gramex will start from the `DIR` when running Gramex. For example:

    gramex run <appname> --dir=subdirectory-name

You can pass any command line options as mentioned in the [config docs](../config/#command-line). For example:

    gramex run <appname> --listen.port=1234

... starts the application on port 1234.

## Uninstalling

To uninstall an app, run:

    gramex uninstall <appname>

This will direct the entire folder where the app was installed. Locally saved data (if any) will be deleted.

To list apps that can be uninstalled, run:

    gramex uninstall
