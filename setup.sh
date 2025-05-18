#!/bin/sh

# Check if USERNAME environment variable is set
if [ -z "$USERNAME" ]; then
  echo "USERNAME environment variable is not set. Exiting."
  exit 1
fi

# Remove *-merged folders
find / -maxdepth 1 -type d -name '*-merged' -exec rm -rf {} +

# Mask getty services to avoid console login prompt
systemctl mask getty@tty1.service getty-static.service

# Start and enable wireguard
if wg-quick up wg0; then
  echo "[*] WireGuard interface wg0 started successfully."
else
  echo "[*] Failed to start WireGuard interface wg0. Exiting."
fi

iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -p tcp -i wg0 --dst 10.5.0.0/16

if service ssh start; then
  echo "[*] SSH service started successfully."
else
  echo "[*] Failed to start SSH service. Exiting."
fi

chmod 775 /home/${USERNAME}
# code-server configuration
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


# Add '${USERNAME}' to the 'docker' group
groupadd docker > /dev/null 2>&1
usermod -aG docker ${USERNAME}


# Create initialization script directory and script
mkdir -p /home/${USERNAME}/.init
cd /home/${USERNAME}/.init
touch docker_init.sh
chmod +x docker_init.sh
chown -R ${USERNAME}:${USERNAME} docker_init.sh

# Run docker_init.sh if it exists


dockerd --host=unix:///var/run/docker.sock &> /var/log/dockerd.log &

echo "Waiting for Docker daemon to be ready…"

sleep 2

if [ -f ./docker_init.sh ]; then
  # replace 'appuser' with your target username
  su ${USERNAME} -c "bash -l -c './docker_init.sh'"
fi
echo "Setup is completed"
tail -f /dev/null
