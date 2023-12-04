#!/bin/bash

chmod +x /app/setup.sh
# Install sudo
yum install -y sudo shadow-utils util-linux

# Create user
export user=ec2-user
useradd -m -p '' ${user}
usermod -aG wheel ${user}
echo "${user} ALL=(ALL) NOPASSWD: ALL" | tee /etc/sudoers.d/${user}

# Run the command as the switched user
su - ${user} -c "/app/setup.sh -d"

su - ${user} -c "source ~/.bashrc"
su - ${user} -c "conda --version"
su - ${user} -c "python --version"
su - ${user} -c "gramex --version"
su - ${user} -c "node --version"
# Exit the user session
exit
