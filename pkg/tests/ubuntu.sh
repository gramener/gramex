#!/bin/bash

cat /etc/os-release
whoami

chmod +x /app/setup.sh
# install sudo
apt update -y && apt install -y sudo

# Create user
export user=ubuntu
adduser --disabled-password --gecos "" ${user}
usermod -aG sudo ${user}
echo "${user} ALL=(ALL) NOPASSWD: ALL" | tee /etc/sudoers.d/${user}
# Run the command as the switched user
su - ${user} -c "/app/setup.sh -d"
# Exit the user session
exit
