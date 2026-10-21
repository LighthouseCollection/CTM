#!/usr/bin/env bash
set -euo pipefail

# CTM VM post-install setup for Debian 12 — Phase 1 (safe)
# Run as root after minimal Debian installation.
# Does NOT change SSH auth or networking. Those are separate steps
# to avoid locking yourself out.

CTM_HOSTNAME="ctm"

echo "=== CTM VM Setup — Phase 1: Base packages and Docker ==="

# Detect primary network interface
NET_IF=$(ip -o -4 route show default | awk '{print $5}' | head -1)
CURRENT_IP=$(ip -4 addr show "$NET_IF" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
echo "Detected interface: $NET_IF with IP $CURRENT_IP"

# 1. Set hostname
hostnamectl set-hostname "$CTM_HOSTNAME"
if ! grep -q "$CTM_HOSTNAME" /etc/hosts; then
    echo "127.0.1.1 $CTM_HOSTNAME" >> /etc/hosts
fi

# 2. Update and install base packages
apt-get update
apt-get upgrade -y
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    htop \
    sudo \
    unattended-upgrades \
    apt-listchanges \
    qemu-guest-agent

systemctl enable --now qemu-guest-agent

# 3. Install Docker Engine
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
    -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

systemctl enable --now docker

# 4. Add admin user to docker group (if the user exists)
if id "admin" &>/dev/null; then
    usermod -aG docker admin
    echo "User 'admin' added to docker group"
fi

# 5. Create CTM directories
mkdir -p /srv/ctm/media /srv/ctm/static /srv/ctm/backups /opt/ctm
if id "admin" &>/dev/null; then
    chown -R admin:admin /srv/ctm /opt/ctm
fi
chmod 750 /srv/ctm/media /srv/ctm/backups

echo "CTM directories created under /srv/ctm and /opt/ctm"

# 6. UFW firewall — allow SSH before enabling
ufw default deny incoming
ufw default allow outgoing
ufw allow from 10.0.0.0/22 to any port 22 proto tcp comment "SSH from LAN"
ufw allow from 10.0.0.0/22 to any port 8000 proto tcp comment "Django from LAN"
ufw --force enable
echo "Firewall configured (SSH open from LAN)"

# 7. Automatic security updates
cat > /etc/apt/apt.conf.d/50unattended-upgrades <<'UUEOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
UUEOF
systemctl enable unattended-upgrades

# 8. Docker daemon config (log limits, address pools)
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'DJEOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5"
  },
  "default-address-pools": [
    {"base": "172.20.0.0/16", "size": 24}
  ]
}
DJEOF
systemctl restart docker

echo ""
echo "=== Phase 1 complete ==="
echo ""
echo "Current IP: $CURRENT_IP on $NET_IF"
echo "SSH is still using password auth — do NOT run phase 2 yet."
echo ""
echo "Next: from AdminPC, deploy your SSH public key, verify key login"
echo "works in a SEPARATE session, then run vm-harden-ssh.sh."
