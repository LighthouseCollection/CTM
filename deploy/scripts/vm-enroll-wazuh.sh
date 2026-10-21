#!/usr/bin/env bash
set -euo pipefail

# CTM VM — Phase 3: Wazuh agent enrollment
# Run as root. Reads enrollment password from environment or prompts.

WAZUH_MANAGER="10.0.0.26"
AGENT_NAME="CTM-VM"

echo "=== Phase 3: Wazuh agent enrollment ==="

if [ -z "${WAZUH_REGISTRATION_PASSWORD:-}" ]; then
    read -rsp "Wazuh enrollment password: " WAZUH_REGISTRATION_PASSWORD
    echo ""
fi

# Add Wazuh repository
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
    gpg --no-default-keyring \
    --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import && \
    chmod 644 /usr/share/keyrings/wazuh.gpg

echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
    > /etc/apt/sources.list.d/wazuh.list

apt-get update

WAZUH_MANAGER="$WAZUH_MANAGER" \
WAZUH_REGISTRATION_PASSWORD="$WAZUH_REGISTRATION_PASSWORD" \
WAZUH_AGENT_NAME="$AGENT_NAME" \
    apt-get install -y wazuh-agent

systemctl daemon-reload
systemctl enable --now wazuh-agent

echo ""
echo "Wazuh agent '$AGENT_NAME' enrolled -> $WAZUH_MANAGER"
