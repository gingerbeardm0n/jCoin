#!/usr/bin/env bash
# Run this ONCE on the VM as root (or via sudo) to enable auto-updates.
# After this, the jcoin-update timer runs hourly, pulls from GitHub,
# runs tests, and restarts the daemon only if tests pass.

set -euo pipefail

# Allow jcoin user to restart the daemon without a password
echo 'jcoin ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart jcoin' \
    > /etc/sudoers.d/jcoin-restart
chmod 0440 /etc/sudoers.d/jcoin-restart

# Make the script executable
chmod +x /opt/jcoin/deploy/auto-update.sh

# Install the systemd units
cp /opt/jcoin/deploy/jcoin-update.service /etc/systemd/system/
cp /opt/jcoin/deploy/jcoin-update.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now jcoin-update.timer

echo "Auto-update timer enabled. Check with: systemctl list-timers jcoin-update"
