#!/usr/bin/env bash
set -euo pipefail

# CTM VM — Set static IP
# Run as root. Changes take effect on next ifup or reboot.
# Keep Proxmox console open in case the new IP doesn't work.

CTM_IP="10.0.0.40"
CTM_GATEWAY="10.0.0.1"
CTM_DNS="10.0.0.1"

NET_IF=$(ip -o -4 route show default | awk '{print $5}' | head -1)
CURRENT_IP=$(ip -4 addr show "$NET_IF" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

echo "Interface: $NET_IF"
echo "Current IP: $CURRENT_IP"
echo "Target IP:  $CTM_IP/22"
echo ""

if [ "$CURRENT_IP" = "$CTM_IP" ]; then
    echo "Already at target IP. Nothing to do."
    exit 0
fi

echo "Writing static config for $NET_IF..."

cat > /etc/network/interfaces.d/"$NET_IF" <<EOF
auto $NET_IF
iface $NET_IF inet static
    address $CTM_IP/22
    gateway $CTM_GATEWAY
    dns-nameservers $CTM_DNS
EOF

echo ""
echo "Static IP written. To apply:"
echo "  Option A (graceful): ifdown $NET_IF && ifup $NET_IF"
echo "  Option B (safe):     reboot"
echo ""
echo "KEEP PROXMOX CONSOLE OPEN. If SSH breaks, use the console to fix"
echo "/etc/network/interfaces.d/$NET_IF"
