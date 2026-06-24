#!/bin/bash
# Run once on a fresh DigitalOcean Ubuntu 22.04 droplet (as root).
# Sets up Python, jCoin, systemd service, and starts the daemon.
#
# Usage:
#   ssh root@YOUR_DROPLET_IP
#   curl -sO https://raw.githubusercontent.com/YOUR_REPO/main/deploy/setup_droplet.sh
#   bash setup_droplet.sh YOUR_KRAKEN_KEY YOUR_KRAKEN_SECRET
#
# Or paste key/secret when prompted.

set -e

KRAKEN_KEY="${1:-}"
KRAKEN_SECRET="${2:-}"

if [[ -z "$KRAKEN_KEY" ]]; then
    read -rp "Kraken demo API key: " KRAKEN_KEY
fi
if [[ -z "$KRAKEN_SECRET" ]]; then
    read -rsp "Kraken demo API secret: " KRAKEN_SECRET
    echo
fi

echo "==> Updating system packages"
apt-get update -qq && apt-get install -y -qq python3.11 python3.11-venv python3-pip git

echo "==> Cloning jCoin"
mkdir -p /opt/jcoin
cd /opt/jcoin

if [[ -d ".git" ]]; then
    git pull
else
    # Replace with your actual repo URL
    git clone https://github.com/YOUR_GITHUB_USER/jCoin.git .
fi

echo "==> Installing Python dependencies"
python3.11 -m venv venv
source venv/bin/activate
pip install --quiet -r requirements.txt

echo "==> Writing .env"
cat > /opt/jcoin/.env <<EOF
KRAKEN_FUTURES_KEY=${KRAKEN_KEY}
KRAKEN_FUTURES_SECRET=${KRAKEN_SECRET}
EOF
chmod 600 /opt/jcoin/.env

echo "==> Creating log directory"
mkdir -p /opt/jcoin/logs

echo "==> Installing systemd service"
cat > /etc/systemd/system/jcoin.service <<EOF
[Unit]
Description=jCoin autonomous trading daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/jcoin
ExecStart=/opt/jcoin/venv/bin/python -m jcoin.live.daemon --mode both
Restart=always
RestartSec=30
StandardOutput=append:/opt/jcoin/logs/daemon.log
StandardError=append:/opt/jcoin/logs/daemon.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jcoin
systemctl start jcoin

echo ""
echo "==> Done. Daemon running as systemd service 'jcoin'."
echo ""
echo "Commands:"
echo "  systemctl status jcoin        # is it running?"
echo "  journalctl -u jcoin -f        # live logs"
echo "  tail -f /opt/jcoin/logs/daemon.log   # daemon log"
echo "  systemctl restart jcoin       # restart after code update"
echo ""
echo "Dashboard (run on droplet):"
echo "  source venv/bin/activate"
echo "  python -m jcoin.dashboard --state-dir kraken_state --port 8765"
echo "  # Then open http://YOUR_DROPLET_IP:8765"
