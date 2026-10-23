#!/usr/bin/env bash
# Run ONCE on the VM as root (re-run after changing any unit file in deploy/):
#   cd /opt/jcoin && sudo bash deploy/setup-auto-update.sh
# Installs the hourly auto-update timer and the daily state-backup timer.

set -euo pipefail

# Let the jcoin user restart the daemon (exact command only) without a password.
TMP=$(mktemp)
echo 'jcoin ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart jcoin' > "$TMP"
visudo -cf "$TMP"
install -m 0440 "$TMP" /etc/sudoers.d/jcoin-restart
rm -f "$TMP"

# git does not track the exec bit reliably here; both scripts are run via /bin/bash.
cp /opt/jcoin/deploy/jcoin-update.service /opt/jcoin/deploy/jcoin-update.timer \
   /opt/jcoin/deploy/jcoin-backup.service /opt/jcoin/deploy/jcoin-backup.timer \
   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now jcoin-update.timer jcoin-backup.timer

echo "Timers enabled. Check with: systemctl list-timers 'jcoin-*'"
