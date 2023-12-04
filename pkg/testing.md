# Testing setup

Tesing the installer script in multiple platforms using docker containers

- Disable path conversion in ***GIT BASH*** (only if using git bash)

  ```sh
  export MSYS_NO_PATHCONV=1 
  ```

## Ubuntu

  ```sh
  cd tests
  ./test_ubuntu.sh
  ```

## Centos 7

  ```sh
  cd tests
  ./test_centos7.sh
  ```

## amazonlinux 2

  ```sh
  cd tests
  ./test_amazon_linux_2.sh
  ```

## Alpine

- Run docker Amazon linux container

  ```sh
  docker run --rm -itv $(pwd):/app -w /app alpine:latest sh
  ```

> TODO: Create a `sh` script that runs in `shell` not `bash`

- Test the installer script

  ```sh
  chmod +x /app/pkg/setup_sh.sh
  /app/pkg/setup_sh.sh
  ```
