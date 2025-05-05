#!/bin/sh

# Check if USERNAME environment variable is set
if [ -z "$USERNAME" ]; then
  echo "USERNAME environment variable is not set. Exiting."
  exit 1
fi

# Create /run/sshd directory
mkdir -p /run/sshd && chmod 0755 /run/sshd

# # Stop and disable ssh.socket to avoid conflicts
# systemctl stop ssh.socket
# systemctl disable ssh.socket

# Start the SSH service
if systemctl start ssh; then
  echo "[*] SSH service started successfully."
else
  echo "[*] Failed to start SSH service. Exiting."
fi

# Start and enable WireGuard
if wg-quick up wg0; then
  echo "[*] WireGuard interface wg0 started successfully."
else
  echo "[*] Failed to start WireGuard interface wg0. Exiting."
fi

chmod 775 /home/${USERNAME}

# Code-server configuration
if [ ! -d "/home/$USERNAME/.config/code-server" ]; then
  mkdir -p /home/$USERNAME/.config/code-server
  cd /home/$USERNAME/.config/code-server
  echo "bind-addr: 0.0.0.0:1111
auth: password
password: $USERNAME@321
cert: false" > docker.yaml
  echo "[*] code-server configuration created."
else
  echo "[*] /home/$USERNAME/.config/code-server already exists. Skipping creation."
fi

# Add user to docker group
usermod -aG docker ${USERNAME}

# Create initialization script directory and script
mkdir -p /home/${USERNAME}/.init
cd /home/${USERNAME}/.init
touch docker_init.sh
chmod +x docker_init.sh
chown -R ${USERNAME}:${USERNAME} docker_init.sh

# Run docker_init.sh if it exists
if [ -f ./docker_init.sh ]; then
    ./docker_init.sh
fi

echo "Setup is completed"
exec /sbin/init --log-level=err
