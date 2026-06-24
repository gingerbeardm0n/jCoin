#!/bin/bash
# One-time setup for Oracle Cloud Always Free Ubuntu 22.04 (ARM or AMD).
#
# Usage:
#   ssh -i ~/your-oracle-key.pem ubuntu@YOUR_ORACLE_IP
#   curl -sO https://raw.githubusercontent.com/YOUR_GITHUB/jCoin/main/deploy/setup_oracle.sh
#   bash setup_oracle.sh
#
# You will be prompted for your Kraken demo API key and secret.

set -e

read -rp  "Kraken demo API key: "    KRAKEN_KEY
read -rsp "Kraken demo API secret: " KRAKEN_SECRET
echo

echo "==> Updating packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip git

echo "==> Cloning jCoin"
cd ~
if [[ -d "jCoin/.git" ]]; then
    cd jCoin && git pull
else
    git clone https://github.com/YOUR_GITHUB_USER/jCoin.git
    cd jCoin
fi

echo "==> Installing Python dependencies"
python3 -m venv venv
source venv/bin/activate
pip install --quiet -r requirements.txt

echo "==> Writing .env"
cat > ~/.jcoin_env <<EOF
KRAKEN_FUTURES_KEY=${KRAKEN_KEY}
KRAKEN_FUTURES_SECRET=${KRAKEN_SECRET}
EOF
chmod 600 ~/.jcoin_env

# Copy .env into repo dir
cp ~/.jcoin_env ~/jCoin/.env

echo "==> Creating log directory"
mkdir -p ~/jCoin/logs

echo "==> Installing systemd service"
sudo bash -c "cat > /etc/systemd/system/jcoin.service" <<EOF
[Unit]
Description=jCoin autonomous trading daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/jCoin
ExecStart=/home/ubuntu/jCoin/venv/bin/python -m jcoin.live.daemon --mode both
Restart=always
RestartSec=30
StandardOutput=append:/home/ubuntu/jCoin/logs/daemon.log
StandardError=append:/home/ubuntu/jCoin/logs/daemon.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jcoin
sudo systemctl start jcoin

echo ""
echo "==> Done! Daemon running."
echo ""
echo "Useful commands:"
echo "  sudo systemctl status jcoin              # running?"
echo "  tail -f ~/jCoin/logs/daemon.log          # live log"
echo "  sudo systemctl restart jcoin             # restart"
echo ""
echo "==> Starting dashboard on port 8765"
echo "  (open this port in Oracle Cloud: Networking -> VCN -> Security List -> add Ingress rule TCP 8765)"
echo ""
echo "Run dashboard:"
echo "  cd ~/jCoin && source venv/bin/activate"
echo "  nohup python -m jcoin.dashboard --state-dir kraken_state --port 8765 &"
echo "  # Access at http://YOUR_ORACLE_IP:8765"
