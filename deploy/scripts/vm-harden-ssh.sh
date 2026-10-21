#!/usr/bin/env bash
set -euo pipefail

# CTM VM — Phase 2: Harden SSH
# Run as root ONLY after verifying key-based login works.
# Test: open a second SSH session with your key before running this.

ADMIN_USER="admin"

echo "=== Phase 2: SSH hardening ==="

# Verify the admin user has at least one authorized key
AUTH_KEYS="/home/$ADMIN_USER/.ssh/authorized_keys"
if [ ! -f "$AUTH_KEYS" ] || [ ! -s "$AUTH_KEYS" ]; then
    echo "ERROR: No authorized_keys found for $ADMIN_USER."
    echo "Deploy your public key first. Aborting to prevent lockout."
    exit 1
fi

KEY_COUNT=$(grep -c '^ssh-' "$AUTH_KEYS" 2>/dev/null || echo 0)
echo "Found $KEY_COUNT SSH public key(s) for $ADMIN_USER"

if [ "$KEY_COUNT" -eq 0 ]; then
    echo "ERROR: authorized_keys exists but contains no valid keys. Aborting."
    exit 1
fi

# Confirm with operator
echo ""
echo "This will disable root login and password authentication."
echo "Make sure you have a SEPARATE SSH session open using your key."
read -rp "Proceed? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Apply hardening
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config

systemctl restart sshd

echo ""
echo "SSH hardened. Root login disabled, password auth disabled."
echo "Test your key login in a NEW session before closing this one."
