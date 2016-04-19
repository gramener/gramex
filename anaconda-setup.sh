# This script creates conda packages on the Gramener channel
# See https://anaconda.org/gramener/packages
#
# This works on a continuumio/anaconda Docker instance.

# Contact s.anand@gramener.com for $ANACONDA_PASSWORD
anaconda login --username gramener --password $ANACONDA_PASSWORD

# Install build dependencies
conda install conda-build anaconda-client

# Loop through packages we want to create. These are packages (+ dependencies)
# that are in requirements.txt but not in conda's default channel.
for package in orderedattrdict xmljson crontab pathlib argh pathtools watchdog
do
  # Create a skeleton from pypi
  conda skeleton pypi $package

  for version in 2.7 3.3 3.4 3.5
  do
    # Build for the version. $path has the output path
    conda build --python $version $package
    path=$(conda build --python $version $package --output)

    # Convert into all platforms in the conda-build/ folder
    rm -rf conda-build/
    conda convert --platform all $path -o conda-build

    # Upload all files from conda-build/
    find conda-build/ -type f | xargs -n 1 anaconda upload
  done
done

rm -rf conda-build/
