# Testing setup

Tesing the installer script in multiple platforms using docker containers

- Disable path conversion in ***GIT BASH*** (only if using git bash)

  ```sh
  export MSYS_NO_PATHCONV=1 
  ```

## Ubuntu

- Run docker ubuntu container

  ```sh
  docker run --rm -itv $(pwd):/app -w /app ubuntu:latest bash
  ```

- Create default user and activate that user in docker ubuntu shell

  ```sh
  # Install sudo
  apt update -y && apt install -y sudo
  # Create user
  export user=ubuntu
  adduser --disabled-password --gecos "" ${user}
  usermod -aG sudo ${user}
  echo "${user} ALL=(ALL) NOPASSWD: ALL" | tee /etc/sudoers.d/${user}
  # Activate user
  su - ${user}
  ```

- Test the installer script

  ```sh
  chmod +x /app/pkg/setup.sh
  /app/pkg/setup.sh
  ```

## Centos 7

- Run docker Centos container

  ```sh
  docker run --rm -itv $(pwd):/app -w /app centos:7 bash
  ```

- Create default user and activate that user in docker ubuntu shell

  ```sh
  # Install sudo
  yum install -y sudo
  # Create user
  export user=centos
  useradd -m -p '' ${user}
  usermod -aG wheel ${user}
  echo "${user} ALL=(ALL) NOPASSWD: ALL" | tee /etc/sudoers.d/${user}
  # Activate user
  su - ${user}
  ```

- Test the installer script

  ```sh
  chmod +x /app/pkg/setup.sh
  /app/pkg/setup.sh
  ```

## amazonlinux 2

- Run docker Amazon linux container

  ```sh
  docker run --rm -itv $(pwd):/app -w /app amazonlinux:2 bash
  ```

- Create default user and activate that user in docker ubuntu shell

  ```sh
  # Install sudo
  yum install -y sudo shadow-utils util-linux

  # Create user
  export user=ec2-user
  useradd -m -p '' ${user}
  usermod -aG wheel ${user}
  echo "${user} ALL=(ALL) NOPASSWD: ALL" | tee /etc/sudoers.d/${user}
  # Activate user
  su - ${user}
  ```

- Test the installer script

  ```sh
  chmod +x /app/pkg/setup.sh
  /app/pkg/setup.sh
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
