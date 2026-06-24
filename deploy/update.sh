#!/bin/bash
# Push latest code to droplet and restart daemon.
# Run from your local machine: bash deploy/update.sh root@YOUR_DROPLET_IP

set -e
HOST="${1:?Usage: update.sh root@DROPLET_IP}"

echo "==> Deploying to $HOST"
ssh "$HOST" "cd /opt/jcoin && git pull && systemctl restart jcoin"
echo "==> Done. Daemon restarted."
echo "==> Logs: ssh $HOST 'tail -f /opt/jcoin/logs/daemon.log'"
