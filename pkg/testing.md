# Testing setup

To test this on Ubuntu:

- Disable path conversion in ***GIT BASH*** (only if using git bash)

  ```sh
  export MSYS_NO_PATHCONV=1 
  ```

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
  su - ubuntu
  ```

- Test the installer script

  ```sh
  /app/pkg/setup.sh
  ```
