#!/usr/bin/env bash
# One-time provisioning for a fresh GCP e2-micro VM (Debian/Ubuntu). Run as root
# (or with sudo) after SSHing in for the first time. See ../DEPLOY_GCP.md for the
# steps before and after this script (VM creation, deploy key, .env, verification).
set -euo pipefail

REPO_URL="git@github.com:gingerbeardm0n/jCoin.git"
APP_DIR="/opt/jcoin"

echo "== installing system packages =="
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "== creating jcoin service user =="
id -u jcoin &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin jcoin

echo "== cloning repo (requires the deploy key already added to GitHub -- see DEPLOY_GCP.md) =="
if [ ! -d "$APP_DIR/.git" ]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    echo "  $APP_DIR already exists, skipping clone (run 'cd $APP_DIR && sudo -u jcoin git pull' to update)"
fi

echo "== python venv + deps =="
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/logs" "$APP_DIR/paper_state" "$APP_DIR/kraken_state"
chown -R jcoin:jcoin "$APP_DIR"

if [ ! -f "$APP_DIR/.env" ]; then
    echo "== NOTE: $APP_DIR/.env does not exist yet =="
    echo "   Create it now (see DEPLOY_GCP.md) with KRAKEN_FUTURES_KEY/SECRET before starting the service."
fi

echo "== installing systemd service =="
cp "$APP_DIR/deploy/jcoin.service" /etc/systemd/system/jcoin.service
systemctl daemon-reload
systemctl enable jcoin

echo "== done. Start it with: sudo systemctl start jcoin =="
echo "   Check status:        sudo systemctl status jcoin"
echo "   Watch logs:           tail -f $APP_DIR/logs/daemon.log"
